import pytest
from fastapi.testclient import TestClient

from sentriflow.api.server import create_app

AUTH = {"authorization": "Bearer test-session"}


@pytest.fixture
def client(runtime):
    with TestClient(
        create_app(runtime, "test-session"),
        base_url="http://127.0.0.1:8787",
        client=("127.0.0.1", 50000),
    ) as client:
        yield client


def test_token_origin_host_and_peer(client, runtime):
    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", headers=AUTH).status_code == 200
    for origin in ("https://evil.test", "null"):
        assert client.get("/api/health", headers=AUTH | {"origin": origin}).status_code == 403
    assert client.get("/api/health", headers=AUTH | {"host": "evil.test:8787"}).status_code == 403
    with TestClient(
        create_app(runtime, "test-session"),
        base_url="http://127.0.0.1:8787",
        client=("192.168.0.5", 50000),
    ) as remote:
        assert remote.get("/api/health", headers=AUTH).status_code == 403


def test_crud_and_secret_non_echo(client):
    pattern = {"label": "canary", "pattern": "private-canary"}
    result = client.post("/api/patterns", headers=AUTH, json=pattern)
    assert result.status_code == 201
    assert "private-canary" not in result.text
    assert "private-canary" not in client.get("/api/snapshot", headers=AUTH).text
    assert client.delete(f"/api/patterns/{result.json()['id']}", headers=AUTH).status_code == 204
    assert (
        client.put("/api/settings", headers=AUTH, json={"halt_timeout_seconds": 0}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/halts/missing/decision", headers=AUTH, json={"action": "allow"}
        ).status_code
        == 409
    )
    assert client.post("/api/system/ca", headers=AUTH, json={"consent": False}).status_code == 422
    # Routing is forbidden while the actual proxy is not running; no registry writes occur.
    assert client.post("/api/system/proxy", headers=AUTH, json={"enabled": True}).status_code == 409
    body = {"process_match": "a" * 64, "host_match": "EXAMPLE.TEST.", "action": "block"}
    created = client.post("/api/rules", headers=AUTH, json=body)
    assert created.status_code == 201
    assert created.json()["host_match"] == "example.test"
    assert client.delete(f"/api/rules/{created.json()['id']}", headers=AUTH).status_code == 204
