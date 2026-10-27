import sqlite3

import pytest

from sentriflow.application import Runtime
from sentriflow.core.models import Alert, Flow, Rule, Verdict
from sentriflow.storage.db import Database


@pytest.mark.asyncio
async def test_reopen_filters_and_cascaded_history_clear(runtime):
    await runtime.open()
    flow = Flow(host="demo.test", pid=1, process_name="browser.exe", verdict=Verdict.BLOCK)
    await runtime.flows.save(flow)
    await runtime.alerts.save(
        Alert(
            flow_id=flow.id,
            type="pii",
            severity="high",
            pattern_label="email",
            masked_sample="[redacted]",
        )
    )
    rule = await runtime.rules.save(Rule(host_match="demo.test", action=Verdict.BLOCK))
    await runtime.settings.save({"tracker_policy": "block"})
    await runtime.close()
    fresh = Runtime(runtime.config)
    await fresh.open()
    try:
        assert fresh.config.tracker_policy == "block"
        assert (await fresh.rules.list())[0].id == rule.id
        assert len(await fresh.flows.list(process="browser.exe", verdict="block")) == 1
        assert not await fresh.flows.list(process="missing.exe")
        assert not await fresh.flows.list(process="' OR 1=1 --")
        await fresh.db.execute("DELETE FROM flows")
        assert not await fresh.alerts.list()
        assert len(await fresh.rules.list()) == 1
    finally:
        await fresh.close()


@pytest.mark.asyncio
async def test_newer_database_is_not_downgraded(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")
    db = Database(path)
    with pytest.raises(ValueError, match="newer"):
        await db.open()
    assert db.connection is None


@pytest.mark.asyncio
async def test_dashboard_migration_preserves_v1_history_and_rules(tmp_path):
    from pathlib import Path

    import sentriflow.storage.db as database_module

    path = tmp_path / "sentriflow.db"
    sql = (
        Path(database_module.__file__).with_name("migrations").joinpath("001_init.sql").read_text()
    )
    with sqlite3.connect(path) as connection:
        connection.executescript(sql)
        connection.execute("PRAGMA user_version=1")
        connection.execute(
            "INSERT INTO flows VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "old-flow",
                "2026-10-27T00:00:00+00:00",
                1,
                "browser.exe",
                None,
                "GET",
                "https",
                "example.test",
                443,
                "/",
                0,
                100,
                "inspected",
                "allow",
                "default",
                None,
                None,
                "[]",
            ),
        )
        connection.execute(
            "INSERT INTO rules VALUES (?,?,?,?,?,?)",
            (
                "old-rule",
                "2026-10-27T00:00:00+00:00",
                "browser.exe",
                "example.test",
                "block",
                "saved",
            ),
        )
    from sentriflow.config import Settings

    fresh = Runtime(Settings(data_dir=tmp_path))
    await fresh.open()
    try:
        flows = await fresh.flows.list()
        rules = await fresh.rules.list()
        assert flows[0].id == "old-flow" and flows[0].bytes_down == 100
        assert flows[0].state == "completed" and flows[0].destination_ip is None
        assert rules[0].id == "old-rule" and rules[0].process_match == "browser.exe"
        assert (await fresh.db.fetch("PRAGMA user_version"))[0]["user_version"] == 2
    finally:
        await fresh.close()


@pytest.mark.asyncio
async def test_different_prototype_schema_is_preserved(tmp_path):
    path = tmp_path / "prototype.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE flows (id TEXT PRIMARY KEY, data TEXT)")
        connection.execute("INSERT INTO flows VALUES ('old', '{\"host\":\"example.test\"}')")
    db = Database(path)
    with pytest.raises(ValueError, match="different prototype schema"):
        await db.open()
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT id FROM flows").fetchone()[0] == "old"
