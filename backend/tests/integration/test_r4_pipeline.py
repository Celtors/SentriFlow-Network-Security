import asyncio
import socket

import httpx
import pytest

from sentriflow.core.models import Verdict
from sentriflow.proxy.process_resolver import ProcessResolver
from sentriflow.proxy.runner import create_master


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def next_pending(runtime):
    async with asyncio.timeout(5):
        while not runtime.halts.pending():
            await asyncio.sleep(0.005)
    return runtime.halts.pending()[0].id


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
    await runtime.open()
    runtime.config.proxy_port = free_port()
    runtime.resolver = ProcessResolver(runtime.config.proxy_port)
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
        await runtime.close()
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
        await runtime.halts.resolve(flow_id, Verdict(action))
        assert (await request).status_code == expected
        assert len(received) == (1 if action == "allow" else 0)
    assert b"student@example.test" in received[0]["body"]
    assert "student@example.test" not in str(await runtime.db.fetch("SELECT * FROM flows"))


async def test_safe_request_and_timeout_block(pipeline, runtime):
    client, url, received, _ = pipeline
    runtime.config.halt_timeout_seconds = 0.1
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
    assert sum(p["interval_down"] for p in runtime._speed.values()) > 0
    release.set()
    response = await request
    assert response.content == b"x" * 1024 + b"y" * 1024
    flow = (await runtime.flows.list())[0]
    assert flow.bytes_down == 2048 and flow.state == "completed"


async def test_binary_halt_and_inspector_fail_closed(pipeline, runtime, monkeypatch):
    client, url, received, _ = pipeline
    request = asyncio.create_task(
        client.post(url, content=b"\xff", headers={"Content-Type": "application/octet-stream"})
    )
    flow_id = await next_pending(runtime)
    assert runtime.halts.pending()[0].flow.tls_status == "not_inspected"
    await runtime.halts.resolve(flow_id, Verdict.BLOCK)
    assert (await request).status_code == 403 and not received

    async def fail(*args, **kwargs):
        raise RuntimeError("Simulated failure")

    monkeypatch.setattr(runtime, "inspect", fail)
    assert (await client.get(url)).status_code == 503 and not received


async def test_tracker_autoblock_and_oversize_body(pipeline, runtime):
    client, url, received, _ = pipeline
    await runtime.blocklist.add("127.0.0.1", "test-only-local-marker")
    runtime.config.tracker_policy = "block"
    assert (await client.get(url)).status_code == 403 and not received
    assert (await runtime.flows.list())[0].verdict == Verdict.BLOCK


async def test_dashboard_cannot_be_routed_back_through_inspection(pipeline, runtime):
    client, _, received, _ = pipeline
    response = await client.get(f"http://127.0.0.1:{runtime.config.api_port}/api/health")
    assert response.status_code == 403 and not received
    assert "bypass" in response.text


async def test_websocket_frames_are_not_forwarded_without_inspection(pipeline):
    client, url, received, _ = pipeline
    response = await client.get(url, headers={"Connection": "Upgrade", "Upgrade": "websocket"})
    assert response.status_code == 403 and not received
