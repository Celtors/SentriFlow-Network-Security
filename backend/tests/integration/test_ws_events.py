import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from sentriflow.api.server import create_app


def test_ws_auth_snapshot_and_settings_events(runtime):
    with TestClient(
        create_app(runtime, "token"), base_url="http://127.0.0.1:8787", client=("127.0.0.1", 40000)
    ) as client:
        origin = {"origin": "http://127.0.0.1:8787"}
        with client.websocket_connect("ws://127.0.0.1:8787/ws", headers=origin) as ws:
            ws.send_json({"token": "token"})
            assert ws.receive_json()["type"] == "snapshot"
            client.put(
                "/api/settings",
                headers={"authorization": "Bearer token"},
                json={"tracker_mode": "block"},
            )
            assert ws.receive_json()["type"] == "settings.updated"
        with (
            pytest.raises(WebSocketDisconnect),
            client.websocket_connect("ws://127.0.0.1:8787/ws", headers=origin) as ws,
        ):
            ws.send_json({"token": "wrong"})
            ws.receive_json()
        with pytest.raises(WebSocketDisconnect), client.websocket_connect("ws://127.0.0.1:8787/ws"):
            pass
