import asyncio
from unittest.mock import AsyncMock

import pytest

from sentriflow.application import Runtime
from sentriflow.config import Settings
from sentriflow.core.models import Flow


async def test_tracker_matcher_is_reused_and_invalidated_after_intel_changes(runtime, monkeypatch):
    await runtime.open()
    try:
        runtime.config.tracker_policy = "block"
        await runtime.blocklist.add("ads.example.test")
        domains = AsyncMock(wraps=runtime.blocklist.domains)
        monkeypatch.setattr(runtime.blocklist, "domains", domains)
        for _ in range(2):
            decision = await runtime.inspect(
                Flow(host="ads.example.test"), "http://ads.example.test", {}, b""
            )
            assert decision.action == "block"
        assert domains.await_count == 1
        await runtime.blocklist.replace_source("manual", {"fresh.example.test"})
        assert (
            await runtime.inspect(
                Flow(host="fresh.example.test"), "http://fresh.example.test", {}, b""
            )
        ).action == "block"
        assert (
            await runtime.inspect(Flow(host="ads.example.test"), "http://ads.example.test", {}, b"")
        ).action == "allow"
        assert domains.await_count == 2
    finally:
        await runtime.close()


async def test_blocklist_loading_does_not_depend_on_geoip_location(tmp_path):
    lists = tmp_path / "intel"
    lists.mkdir()
    (lists / "stevenblack-hosts.txt").write_text("0.0.0.0 tracker.example.test\n")
    runtime = Runtime(
        Settings(
            data_dir=tmp_path / "data",
            blocklist_dir=lists,
            geoip_database=tmp_path / "elsewhere" / "country.mmdb",
        )
    )
    await runtime.open()
    try:
        assert await runtime.blocklist.domains() == ["tracker.example.test"]
        assert runtime.geoip.status()["available"] is False
    finally:
        await runtime.close()


def test_reconnect_restores_pending_halt_without_releasing_it(client, runtime):
    flow = Flow(host="example.test")
    task = client.portal.start_task_soon(runtime.halts.hold, flow, 5)

    async def wait_pending():
        async with asyncio.timeout(3):
            while not runtime.halts.pending():
                await asyncio.sleep(0.001)

    client.portal.call(wait_pending)
    for _ in range(2):
        with client.websocket_connect(
            "ws://127.0.0.1:8787/ws",
            headers={"Origin": "http://127.0.0.1:8787"},
            subprotocols=["sentriflow", runtime.token],
        ) as socket:
            initial = socket.receive_json()
            assert initial["type"] == "system.status"
            assert initial["data"]["snapshot"]["pending"][0]["id"] == flow.id
        assert not task.done()
    assert (
        client.post(f"/api/halts/{flow.id}/decision", json={"action": "block"}).status_code == 200
    )
    assert task.result(timeout=2).action == "block"


@pytest.mark.parametrize(
    "path,body,event_type",
    [
        ("/rules", {"host_match": "example.test", "action": "block"}, "rules.updated"),
        ("/patterns", {"label": "private", "pattern": "private-marker"}, "patterns.updated"),
        ("/settings", {"tracker_policy": "block"}, "settings.updated"),
    ],
)
def test_changes_from_another_client_publish_resync_events(client, runtime, path, body, event_type):
    with client.websocket_connect(
        "ws://127.0.0.1:8787/ws",
        headers={"Origin": "http://127.0.0.1:8787"},
        subprotocols=["sentriflow", runtime.token],
    ) as socket:
        socket.receive_json()
        response = client.request(
            "PUT" if path == "/settings" else "POST", "/api" + path, json=body
        )
        assert response.is_success
        event = socket.receive_json()
        assert event["type"] == event_type
        assert "private-marker" not in str(event)
