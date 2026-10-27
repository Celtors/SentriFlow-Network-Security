import asyncio
import socket

import httpx
import pytest

from sentriflow.core.models import Decision, Settings, Verdict
from sentriflow.proxy.runner import create_master


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def next_pending(runtime):
    async with asyncio.timeout(5):
        while not runtime.halts.pending:
            await asyncio.sleep(0.005)
    return next(iter(runtime.halts.pending))


@pytest.fixture
async def pipeline(runtime):
    received, tasks = [], set()
    release_stream = asyncio.Event()

    async def origin(reader, writer):
        tasks.add(asyncio.current_task())
        try:
            headers = await reader.readuntil(b"\r\n\r\n")
            length = next(
                (
                    int(line.split(b":", 1)[1])
                    for line in headers.split(b"\r\n")
                    if line.lower().startswith(b"content-length:")
                ),
                0,
            )
            # Mark headers immediately as well as body: neither may arrive before a decision.
            received.append({"headers": headers, "body": await reader.readexactly(length)})
            if b" /stream " in headers:
                writer.write(
                    b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n"
                    b"Connection: close\r\n\r\n400\r\n" + b"x" * 1024 + b"\r\n"
                )
                await writer.drain()
                await release_stream.wait()
                writer.write(b"400\r\n" + b"y" * 1024 + b"\r\n0\r\n\r\n")
            else:
                writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK")
            await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            tasks.discard(asyncio.current_task())
            writer.close()
            try:
                await writer.wait_closed()
            except ConnectionError:
                pass

    server = await asyncio.start_server(origin, "127.0.0.1", 0)
    origin_port = server.sockets[0].getsockname()[1]
    runtime.config.proxy_port = free_port()
    master = create_master(runtime)
    running = asyncio.create_task(master.run())
    try:
        async with asyncio.timeout(10):
            while not runtime.proxy_running:
                if running.done():
                    running.result()
                await asyncio.sleep(0.01)
        async with httpx.AsyncClient(
            proxy=f"http://127.0.0.1:{runtime.config.proxy_port}", trust_env=False, timeout=10
        ) as client:
            yield client, f"http://127.0.0.1:{origin_port}", received, release_stream
    finally:
        release_stream.set()
        runtime.halts.shutdown()
        master.shutdown()
        await running
        server.close()
        await server.wait_closed()
        for task in tuple(tasks):
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


async def test_hold_before_forward_block_and_allow(pipeline, runtime):
    client, url, received, _ = pipeline
    for action, expected in (("block", 403), ("allow", 200)):
        request = asyncio.create_task(
            client.post(
                url + "/submit", json={"email": "student@example.test", "card": "4111111111111111"}
            )
        )
        flow_id = await next_pending(runtime)
        assert not received, "HTTP request reached origin before a decision"
        runtime.decide(flow_id, Decision(action=action))
        assert (await request).status_code == expected
        assert len(received) == (1 if action == "allow" else 0)
    assert b"student@example.test" in received[0]["body"]
    assert "student@example.test" not in "\n".join(runtime.db.connection.iterdump())


async def test_safe_request_and_timeout_block(pipeline, runtime):
    client, url, received, _ = pipeline
    runtime.set_settings(Settings(halt_timeout_seconds=2))
    assert (
        await client.post(url, content="hello", headers={"Content-Type": "text/plain"})
    ).status_code == 200
    assert len(received) == 1
    received.clear()
    assert (await client.post(url, json={"email": "student@example.test"})).status_code == 403
    assert not received


async def test_download_is_counted_before_response_completes(pipeline, runtime):
    client, url, _, release = pipeline
    request = asyncio.create_task(client.get(url + "/stream"))
    async with asyncio.timeout(5):
        while not any(flow.bytes_down > 0 for flow in runtime.active.values()):
            await asyncio.sleep(0.01)
    assert not request.done(), "Stream should still be waiting for its second chunk"
    tick = runtime.tick()
    assert tick["download_bps"] > 0
    release.set()
    response = await request
    assert response.content == b"x" * 1024 + b"y" * 1024
    flow = runtime.flows.list()[0]
    assert flow.bytes_down == 2048 and flow.state == "completed"


async def test_binary_halt_and_inspector_fail_closed(pipeline, runtime, monkeypatch):
    client, url, received, _ = pipeline
    request = asyncio.create_task(
        client.post(url, content=b"\xff", headers={"Content-Type": "application/octet-stream"})
    )
    flow_id = await next_pending(runtime)
    assert runtime.halts.pending[flow_id][0].tls_status == "not_inspected"
    runtime.decide(flow_id, Decision(action="block"))
    assert (await request).status_code == 403 and not received

    async def fail(_):
        raise RuntimeError("Simulated failure")

    monkeypatch.setattr(runtime, "inspect_decision", fail)
    assert (await client.get(url)).status_code == 503 and not received


async def test_tracker_autoblock_and_oversize_body(pipeline, runtime):
    client, url, received, _ = pipeline
    runtime.blocklist.add({"127.0.0.1"}, "test-only-local-marker")
    runtime.set_settings(Settings(tracker_mode="block"))
    assert (await client.get(url)).status_code == 403 and not received
    assert runtime.flows.list()[0].verdict == Verdict.BLOCK
