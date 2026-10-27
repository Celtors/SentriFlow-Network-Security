"""S33: no raw dummy PII may reach the disk (SQLite file, its WAL, logs) or the log output.

The verification harness already checks API/event output. This looks at the actual bytes on disk,
which is the stronger evidence for the "never store full payloads" rule.
"""

import asyncio
import gzip
import json
import logging
import sqlite3
from pathlib import Path
from urllib.parse import quote, quote_plus

import pytest

from sentriflow.verification import local_stack

# Configured by the harness as a custom pattern, so it is legitimately stored in custom_patterns.
CONFIGURED_PATTERN = "Alex Example"
# Present in body, query and header of every request but never configured anywhere: if it shows up
# on disk, some code path stored raw request data.
MARKER = "ZZMARK-9137-private-value"
SECRETS = ("alex@example.test", CONFIGURED_PATTERN, "4111111111111111", MARKER)
RAW_SECRETS = tuple(secret for secret in SECRETS if secret != CONFIGURED_PATTERN)
PAYLOADS = [
    (b'{"name":"Alex Example","email":"alex@example.test","card":"4111111111111111"}', "json"),
    (b"name=Alex+Example&email=alex%40example.test&card=4111111111111111", "form"),
    (
        b'--demo\r\nContent-Disposition: form-data; name="d"\r\n\r\n'
        b"Alex Example alex@example.test 4111111111111111\r\n--demo--\r\n",
        "multipart",
    ),
]
CONTENT_TYPES = {
    "json": "application/json",
    "form": "application/x-www-form-urlencoded",
    "multipart": "multipart/form-data; boundary=demo",
}


def spellings(secrets: tuple[str, ...] = SECRETS) -> list[bytes]:
    """Every plausible way a secret could be written: plain, percent-encoded, UTF-16."""
    forms: set[str] = set()
    for secret in secrets:
        forms |= {secret, quote(secret), quote_plus(secret), secret.upper(), secret.lower()}
    encoded = {form.encode() for form in forms} | {form.encode("utf-16-le") for form in forms}
    return sorted(encoded)


def find_leaks(data: bytes, secrets: tuple[str, ...] = SECRETS) -> list[bytes]:
    return [needle for needle in spellings(secrets) if needle in data]


def files_under(directory: Path) -> list[Path]:
    return [p for p in directory.rglob("*") if p.is_file() and p.suffix not in {".pem", ".p12"}]


def leaks_in_directory(directory: Path) -> dict[str, list[bytes]]:
    """Raw-byte scan of every file (database, WAL, logs). The configured pattern is excluded here
    and checked table by table instead."""
    found = {}
    for path in files_under(directory):
        try:
            hits = find_leaks(path.read_bytes(), RAW_SECRETS)
        except PermissionError:  # a file the writer holds exclusively; scanned again after close
            continue
        if hits:
            found[path.name] = hits
    return found


def leaks_in_tables(database: Path) -> dict[str, list[bytes]]:
    """Every table except custom_patterns (which must hold the user's own strings) is scanned."""
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        tables = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
            if row[0] != "custom_patterns" and not row[0].startswith("sqlite_")
        ]
        found = {}
        for table in tables:
            text = json.dumps(connection.execute(f"SELECT * FROM {table}").fetchall(), default=str)
            if hits := find_leaks(text.encode()):
                found[table] = hits
        return found
    finally:
        connection.close()


def test_the_detector_itself_works():
    """Negative control: a scanner that can never fire proves nothing."""
    assert find_leaks(b"xx alex@example.test yy")
    assert find_leaks(b"card=4111111111111111")
    assert find_leaks("alex@example.test".encode("utf-16-le"))
    assert find_leaks(b"name=Alex+Example")
    assert find_leaks(b"name=Alex%20Example")
    assert not find_leaks(b"[redacted] and a***@example.test")


@pytest.mark.asyncio
async def test_no_raw_pii_in_database_wal_or_logs(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    async with local_stack(tmp_path) as (rt, api, proxy, ws, received, http_port, https_port):
        base = f"http://127.0.0.1:{http_port}"

        async def post_and_block(url: str, body: bytes, content_type: str, gz: bool) -> None:
            headers = {"Content-Type": content_type, "X-Private": MARKER}
            url = f"{url}?token={MARKER}"
            if gz:
                body, headers["Content-Encoding"] = gzip.compress(body), "gzip"
            task = asyncio.create_task(proxy.post(url, content=body, headers=headers))
            while True:
                message = json.loads(await asyncio.wait_for(ws.recv(), 5))
                if message["type"] == "halt.requested":
                    break
            await ws.send(
                json.dumps(
                    {
                        "type": "halt.decide",
                        "data": {"id": message["data"]["id"], "action": "block", "scope": "once"},
                    }
                )
            )
            assert (await task).status_code == 403

        for body, kind in PAYLOADS:
            body = (
                body + MARKER.encode()
                if kind != "json"
                else body.replace(b"}", b',"m":"%s"}' % MARKER.encode())
            )
            for gz in (False, True):
                await post_and_block(base + "/submit", body, CONTENT_TYPES[kind], gz)
                await post_and_block(
                    f"https://127.0.0.1:{https_port}/submit", body, CONTENT_TYPES[kind], gz
                )
        assert received == []  # nothing blocked ever reached the upstream server

        # The database is still open here, so recent writes may sit in the -wal file.
        database = tmp_path / "sentriflow.db"
        assert database.exists() and database.stat().st_size > 0
        assert (
            b"127.0.0.1"
            in database.read_bytes() + database.with_name(database.name + "-wal").read_bytes()
        )
        assert leaks_in_directory(tmp_path) == {}
        assert leaks_in_tables(database) == {}
        flows = (await api.get("/api/flows?limit=1000")).json()
        assert len(flows) >= 12  # 3 payloads x 2 encodings x 2 schemes, so the scan had data

    assert leaks_in_directory(tmp_path) == {}, "raw PII found on disk after shutdown"
    assert leaks_in_tables(database) == {}, "raw PII found in a table after shutdown"
    leaking = {}
    for record in caplog.records:
        message = record.getMessage()
        if hits := find_leaks(message.encode()):
            # aiosqlite logs bound SQL parameters at DEBUG. Only the user's own configured pattern
            # (custom_patterns) may appear there; httpx is the test client printing its own URLs.
            allowed = record.name == "httpx" or (
                record.name == "aiosqlite" and "custom_patterns" in message
            )
            if not allowed:
                leaking.setdefault(record.name, []).extend(hits)
    assert leaking == {}, f"raw PII found in log output of: {sorted(leaking)}"


def test_application_logging_does_not_enable_sql_parameter_logging(tmp_path):
    """aiosqlite prints every bound SQL parameter at DEBUG, so it must stay off in the app."""
    from sentriflow.logging_setup import configure_logging

    app_logger = logging.getLogger("sentriflow")
    saved = list(app_logger.handlers), app_logger.level, app_logger.propagate
    try:
        configure_logging(tmp_path, "DEBUG")
        assert not logging.getLogger("aiosqlite").isEnabledFor(logging.DEBUG)
    finally:
        for handler in app_logger.handlers:
            handler.close()
        app_logger.handlers[:] = saved[0]
        app_logger.setLevel(saved[1])
        app_logger.propagate = saved[2]
