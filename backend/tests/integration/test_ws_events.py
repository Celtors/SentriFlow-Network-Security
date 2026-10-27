import pytest
from starlette.websockets import WebSocketDisconnect

from sentriflow.core.models import Flow


def test_event_delivery_and_halt_decision(client, runtime):
    with client.websocket_connect(
        "ws://127.0.0.1:8787/ws",
        headers={"Origin": "http://127.0.0.1:8787"},
        subprotocols=["sentriflow", runtime.token],
    ) as ws:
        assert ws.receive_json()["type"] == "system.status"
        flow = Flow(host="demo.test")
        task = client.portal.start_task_soon(runtime.halts.hold, flow, 5)
        event = ws.receive_json()
        assert event["type"] == "halt.requested"
        assert event["data"]["id"] == flow.id
        ws.send_json(
            {"type": "halt.decide", "data": {"id": flow.id, "action": "block", "scope": "always"}}
        )
        assert ws.receive_json()["type"] == "halt.resolved"
        assert task.result(timeout=2).action == "block"
        assert client.get("/api/rules").json()[0]["host_match"] == "demo.test"


@pytest.mark.parametrize(
    "origin,protocols",
    [
        ("https://attacker.test", ["sentriflow", "TOKEN"]),
        (None, ["sentriflow", "TOKEN"]),
        ("http://127.0.0.1:8787", ["sentriflow", "wrong"]),
    ],
)
def test_ws_rejects_untrusted_clients(client, runtime, origin, protocols):
    protocols = [runtime.token if p == "TOKEN" else p for p in protocols]
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "ws://127.0.0.1:8787/ws",
            headers={"Origin": origin} if origin else {},
            subprotocols=protocols,
        ):
            pass
