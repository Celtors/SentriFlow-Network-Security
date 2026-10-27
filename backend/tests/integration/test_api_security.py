import pytest


@pytest.mark.parametrize(
    "headers,expected",
    [
        ({"X-SentriFlow-Token": ""}, 401),
        ({"Origin": "https://attacker.test"}, 403),
        ({"Origin": "null"}, 403),
        ({"Host": "attacker.test:8787"}, 403),
        ({"Host": "127.0.0.1:9999"}, 403),
        ({"Sec-Fetch-Site": "cross-site"}, 403),
        ({"Origin": "http://127.0.0.1:8787"}, 200),
        ({"Origin": "http://localhost:3000"}, 200),
    ],
)
def test_rest_session_checks(client, headers, expected):
    response = client.get("/api/health", headers=headers)
    assert response.status_code == expected
    assert "access-control-allow-origin" not in response.headers


def test_rules_settings_patterns_and_history(client):
    assert client.post("/api/rules", json={"action": "allow"}).status_code == 422
    response = client.post("/api/rules", json={"action": "block", "host_match": "example.test"})
    assert response.status_code == 201
    rule = response.json()
    assert client.get("/api/rules").json()[0]["id"] == rule["id"]
    assert (
        client.put(
            f"/api/rules/{rule['id']}", json={"action": "allow", "process_match": "browser.exe"}
        ).status_code
        == 200
    )
    assert client.delete(f"/api/rules/{rule['id']}").status_code == 204
    assert client.delete(f"/api/rules/{rule['id']}").status_code == 404
    assert client.put("/api/settings", json={"api_port": 9000}).status_code == 422
    assert client.put("/api/settings", json={"halt_timeout_seconds": 0}).status_code == 422
    assert client.put("/api/settings", json={"inspection_enabled": False}).status_code == 200
    assert client.get("/api/settings").json()["inspection_enabled"] is False
    assert (
        client.post(
            "/api/patterns", json={"label": "bad", "pattern": "[", "is_regex": True}
        ).status_code
        == 422
    )
    pattern = client.post("/api/patterns", json={"label": "test", "pattern": "Alex Example"}).json()
    assert client.delete(f"/api/patterns/{pattern['id']}").status_code == 204
    assert client.get("/api/flows?limit=1001").status_code == 422
    assert client.get("/api/flows?offset=-1").status_code == 422
    assert client.get("/api/flows").json() == []
    assert client.get("/api/score").json()["score"] == 100
    assert client.post("/api/halts/missing/decision", json={"action": "allow"}).status_code == 409
    assert client.post("/api/system/ca", json={"confirmed": False}).status_code == 422


def test_settings_persist_across_restart(client, runtime):
    client.put("/api/settings", json={"tracker_policy": "block"})
    assert client.portal.call(runtime.settings.load)["tracker_policy"] == "block"
