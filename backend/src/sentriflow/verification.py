"""Offline HTTP/HTTPS → proxy → API/WS → decision → SQLite rehearsal.

Run with the development dependencies installed. Never changes OS proxy or CA trust.
"""

import argparse
import asyncio
import gzip
import ipaddress
import json
import platform
import socket
import ssl
import statistics
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from websockets.asyncio.client import connect

from sentriflow.api.server import create_app
from sentriflow.application import Runtime
from sentriflow.config import Settings
from sentriflow.core.models import CustomPattern
from sentriflow.os_adapters.windows.cert_store import prepare_ca
from sentriflow.proxy.runner import create_master


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def server_certificate(directory: Path) -> tuple[Path, Path]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / "upstream-cert.pem", directory / "upstream-key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return cert_path, key_path


@asynccontextmanager
async def local_stack(directory: Path):
    api_port, proxy_port = free_port(), free_port()
    while proxy_port == api_port:
        proxy_port = free_port()
    runtime = Runtime(
        Settings(
            data_dir=directory, api_port=api_port, proxy_port=proxy_port, halt_timeout_seconds=2
        )
    )
    received = []

    async def upstream(reader, writer):
        try:
            head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), 5)
            headers = {}
            for line in head.split(b"\r\n")[1:]:
                if b":" in line:
                    key, value = line.split(b":", 1)
                    headers[key.strip().lower()] = value.strip()
            size = int(headers.get(b"content-length", b"0"))
            await reader.readexactly(size)
            received.append(size)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK")
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError, TimeoutError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    http_server = await asyncio.start_server(upstream, "127.0.0.1", 0)
    cert, key = server_certificate(directory)
    server_ssl = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ssl.load_cert_chain(cert, key)
    https_server = await asyncio.start_server(upstream, "127.0.0.1", 0, ssl=server_ssl)
    http_port, https_port = (
        http_server.sockets[0].getsockname()[1],
        https_server.sockets[0].getsockname()[1],
    )
    await runtime.open()
    await runtime.patterns.save(
        CustomPattern(id="demo-name", label="Demo name", pattern="Alex Example")
    )
    await runtime.blocklist.add("localhost", "synthetic loopback tracker")
    prepare_ca(runtime.config.ca_dir)
    master = create_master(runtime)
    master.options.update(ssl_verify_upstream_trusted_ca=str(cert))
    api_server = uvicorn.Server(
        uvicorn.Config(
            create_app(runtime),
            host="127.0.0.1",
            port=api_port,
            access_log=False,
            log_level="critical",
            ws="websockets-sansio",
        )
    )
    tasks = [asyncio.create_task(master.run()), asyncio.create_task(api_server.serve())]
    try:
        for _ in range(200):
            for task in tasks:
                if task.done():
                    task.result()
                    raise RuntimeError("Local verification service stopped")
            if api_server.started and runtime.proxy_running:
                break
            await asyncio.sleep(0.025)
        else:
            raise TimeoutError("Local verification services did not start")
        client_ssl = ssl.create_default_context(
            cafile=str(runtime.config.ca_dir / "mitmproxy-ca-cert.pem")
        )
        async with (
            httpx.AsyncClient(
                base_url=f"http://127.0.0.1:{api_port}",
                trust_env=False,
                headers={"X-SentriFlow-Token": runtime.token},
            ) as api,
            httpx.AsyncClient(
                proxy=f"http://127.0.0.1:{proxy_port}",
                verify=client_ssl,
                trust_env=False,
                timeout=10,
            ) as proxy,
            connect(
                f"ws://127.0.0.1:{api_port}/ws",
                proxy=None,
                origin=f"http://127.0.0.1:{api_port}",
                subprotocols=["sentriflow", runtime.token],
            ) as ws,
        ):
            yield runtime, api, proxy, ws, received, http_port, https_port
    finally:
        runtime.halts.shutdown()
        master.shutdown()
        api_server.should_exit = True
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 5)
        http_server.close()
        https_server.close()
        await http_server.wait_closed()
        await https_server.wait_closed()
        await runtime.close()


async def measure(repetitions: int = 3) -> dict:
    timings, ordinary, direct, rehearsals, captured_events = [], [], [], [], []
    detected, expected, tls_inspected = 0, 0, False
    with tempfile.TemporaryDirectory(prefix="sentriflow-verification-") as temporary:
        async with local_stack(Path(temporary)) as stack:
            rt, api, proxy, ws, received, http_port, https_port = stack
            base = f"http://127.0.0.1:{http_port}"

            async def event(kind):
                while True:
                    message = json.loads(await asyncio.wait_for(ws.recv(), 5))
                    captured_events.append(message)
                    if message["type"] == kind:
                        return message["data"]

            async def held(request, action="block", scope="once"):
                before = len(received)
                task = asyncio.create_task(request)
                halt = await event("halt.requested")
                assert not task.done(), "Request was released before user decision"
                assert len(received) == before, "Held request reached upstream"
                started = time.perf_counter()
                ws_command = {
                    "type": "halt.decide",
                    "data": {"id": halt["id"], "action": action, "scope": scope},
                }
                await ws.send(json.dumps(ws_command))
                response = await task
                timings.append((time.perf_counter() - started) * 1000)
                assert response.status_code == (403 if action == "block" else 200)
                assert len(received) == before + (action == "allow")
                await event("flow.completed")
                return halt

            async with httpx.AsyncClient(trust_env=False) as plain:
                for _ in range(10):
                    started = time.perf_counter()
                    assert (await plain.get(base + "/normal")).status_code == 200
                    direct.append((time.perf_counter() - started) * 1000)
                    started = time.perf_counter()
                    assert (await proxy.get(base + "/normal")).status_code == 200
                    ordinary.append((time.perf_counter() - started) * 1000)
            for repeat in range(repetitions):
                # Tracker ask policy, with no network or public blocklist download.
                tracker = await held(proxy.get(f"http://localhost:{http_port}/tracker"))
                assert any(f["type"] == "tracker" for f in tracker["flow"]["findings"])
                # Allow a dummy leak, then block it: the score must recover by five points.
                await held(
                    proxy.post(base + "/submit", json={"email": "alex@example.test"}), "allow"
                )
                prior = (await api.get("/api/score")).json()["score"]
                await held(proxy.post(base + "/submit", json={"email": "alex@example.test"}))
                after = (await api.get("/api/score")).json()["score"]
                assert after == min(100, prior + 5)
                rehearsals.append(
                    {
                        "run": repeat + 1,
                        "tracker_halted": True,
                        "pii_blocked": True,
                        "score_before_block": prior,
                        "score_after_block": after,
                    }
                )
            payloads = [
                (
                    b'{"name":"Alex Example","email":"alex@example.test",'
                    b'"card":"4111111111111111"}',
                    "application/json",
                ),
                (
                    b"name=Alex+Example&email=alex%40example.test&card=4111111111111111",
                    "application/x-www-form-urlencoded",
                ),
                (
                    b'--demo\r\nContent-Disposition: form-data; name="data"\r\n\r\n'
                    b"Alex Example alex@example.test 4111111111111111\r\n--demo--\r\n",
                    "multipart/form-data; boundary=demo",
                ),
            ]
            for body, content_type in payloads:
                for compressed in (False, True):
                    headers = {"Content-Type": content_type}
                    content = gzip.compress(body) if compressed else body
                    if compressed:
                        headers["Content-Encoding"] = "gzip"
                    halt = await held(
                        proxy.post(
                            f"https://127.0.0.1:{https_port}/submit",
                            content=content,
                            headers=headers,
                        )
                    )
                    labels = {f["label"] for f in halt["flow"]["findings"]}
                    expected += 3
                    detected += len(labels & {"Demo name", "Email address", "Payment card (Luhn)"})
                    tls_inspected |= halt["flow"]["tls_status"] == "inspected"
            # A saved rule must apply to the next connection without another prompt.
            await held(
                proxy.post(base + "/submit", json={"email": "alex@example.test"}), scope="always"
            )
            before = len(received)
            assert (
                await proxy.post(base + "/submit", json={"email": "alex@example.test"})
            ).status_code == 403
            await event("flow.completed")
            assert len(received) == before
            for rule in (await api.get("/api/rules")).json():
                assert (await api.delete("/api/rules/" + rule["id"])).status_code == 204
            await api.put("/api/settings", json={"halt_timeout_seconds": 0.1})
            before = len(received)
            assert (
                await proxy.post(base + "/timeout", json={"email": "alex@example.test"})
            ).status_code == 403
            await event("flow.completed")
            assert len(received) == before
            flows = (await api.get("/api/flows?limit=1000")).json()
            assert any(f["verdict_source"] == "timeout" for f in flows)
            alerts = (await api.get("/api/alerts?limit=1000")).json()
            persisted = json.dumps({"flows": flows, "alerts": alerts, "events": captured_events})
            assert all(
                secret not in persisted
                for secret in ("alex@example.test", "Alex Example", "4111111111111111")
            )
            named = sum(f["pid"] is not None and f["process_name"] != "Unknown" for f in flows)
    return {
        "measured_at": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "scope": "Automated loopback HTTP/HTTPS backend rehearsal; not a Windows browser session",
        "rehearsals": rehearsals,
        "captured_flows": len(flows),
        "named_flows": named,
        "attribution_percent": round(100 * named / len(flows), 2),
        "seeded_pii_expected": expected,
        "seeded_pii_detected": detected,
        "seeded_pii_detection_percent": round(100 * detected / expected, 2),
        "decision_max_ms": round(max(timings), 2),
        "decision_median_ms": round(statistics.median(timings), 2),
        "non_halted_median_ms": round(statistics.median(ordinary), 2),
        "direct_median_ms": round(statistics.median(direct), 2),
        "https_inspected": tls_inspected,
        "blocked_payloads_never_reached_upstream": True,
        "saved_rule_reused": True,
        "timeout_blocked": True,
        "persisted_samples_redacted": True,
        "pending_manual_evidence": [
            "Windows 11 browser attribution over 10 minutes",
            "Current-user CA consent, HTTPS browser trust and removal",
            "Windows real registry restoration after normal exit and forced termination",
            "Frontend click-through rehearsal, screenshots and backup recording",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/kpis.json"))
    args = parser.parse_args()
    report = asyncio.run(measure())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
