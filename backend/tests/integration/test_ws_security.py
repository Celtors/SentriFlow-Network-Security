"""S18: WebSocket and malformed-token security checks (REST basics live in test_api_security)."""

import pytest
from starlette.websockets import WebSocketDisconnect

ORIGIN = {"Origin": "http://127.0.0.1:8787"}


# TestClient sends "Host: testserver" on WebSockets, which the Host check would (rightly) reject
# and make every bad-handshake test pass for the wrong reason. Always send the real host.
HOST = {"Host": "127.0.0.1:8787"}


def connect(client, protocols, headers=None):
    merged = {**HOST, **(ORIGIN if headers is None else headers)}
    return client.websocket_connect("/ws", subprotocols=protocols, headers=merged)


def test_good_handshake_gets_status_first(client, runtime):
    with connect(client, ["sentriflow", runtime.token]) as ws:
        assert ws.receive_json()["type"] == "system.status"


@pytest.mark.parametrize(
    ("protocols", "headers"),
    [
        (["sentriflow"], ORIGIN),  # no token
        (["sentriflow", "wrong"], ORIGIN),  # wrong token
        (["wrong-name", "TOKEN"], ORIGIN),  # wrong protocol name (TOKEN replaced below)
        (["sentriflow", "TOKEN"], {}),  # browser must send Origin on /ws
        (["sentriflow", "TOKEN"], {"Origin": "https://attacker.test"}),
        (["sentriflow", "TOKEN"], {"Origin": "null"}),
        (["sentriflow", "TOKEN"], {**ORIGIN, "Host": "attacker.test:8787"}),
        (["sentriflow", "TOKEN"], {**ORIGIN, "Host": "127.0.0.1:9999"}),
    ],
)
def test_bad_handshakes_are_closed(client, runtime, protocols, headers):
    protocols = [runtime.token if p == "TOKEN" else p for p in protocols]
    with pytest.raises(WebSocketDisconnect) as err, connect(client, protocols, headers):
        pass
    assert err.value.code == 1008


def test_oversized_client_message_closes_socket(client, runtime):
    with connect(client, ["sentriflow", runtime.token]) as ws:
        ws.receive_json()  # system.status
        ws.send_text("x" * 5000)
        with pytest.raises(WebSocketDisconnect) as err:
            ws.receive_json()
        assert err.value.code == 1009


def test_garbage_client_message_closes_socket(client, runtime):
    with connect(client, ["sentriflow", runtime.token]) as ws:
        ws.receive_json()
        ws.send_text("not json")
        with pytest.raises(WebSocketDisconnect) as err:
            ws.receive_json()
        assert err.value.code == 1008


def test_non_ascii_rest_token_is_401_not_500(client):
    """secrets.compare_digest(str, str) raises TypeError on non-ASCII input."""
    response = client.get("/api/health", headers={"X-SentriFlow-Token": "café".encode("latin-1")})
    assert response.status_code == 401


def test_non_ascii_bearer_token_is_401_not_500(client):
    response = client.get(
        "/api/health",
        headers={"Authorization": b"Bearer caf\xe9", "X-SentriFlow-Token": ""},
    )
    assert response.status_code == 401
