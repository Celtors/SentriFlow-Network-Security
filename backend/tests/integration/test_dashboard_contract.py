import asyncio

from sentriflow.core.models import Flow


def test_dashboard_snapshot_matches_settings_rules_and_public_patterns(client):
    secret = "private-pattern-value"
    pattern = client.post("/api/patterns", json={"label": "Test secret", "pattern": secret})
    assert pattern.status_code == 201
    rule = client.post(
        "/api/rules",
        json={
            "process_match": "a" * 64,
            "process_name": "browser.exe",
            "host_match": "example.test",
            "action": "block",
        },
    )
    assert rule.status_code == 201
    rule_id = rule.json()["id"]
    assert (
        client.put(
            f"/api/rules/{rule_id}",
            json={
                "process_match": "a" * 64,
                "process_name": "browser.exe",
                "host_match": "example.test",
                "action": "allow",
            },
        ).status_code
        == 200
    )
    settings = {"large_upload_bytes": 2000000, "tracker_policy": "block"}
    assert client.put("/api/settings", json=settings).status_code == 200
    response = client.get("/api/snapshot")
    assert response.status_code == 200
    body = response.json()
    assert len(body["rules"]) == 1 and body["rules"][0]["id"] == rule_id
    assert body["rules"][0]["process_name"] == "browser.exe"
    assert body["settings"]["large_upload_bytes"] == 2000000
    assert body["settings"]["tracker_policy"] == "block"
    assert "pattern" not in body["patterns"][0] and secret not in response.text
    assert "proxy_address" in body["system"] and "public_certificate" in body["system"]["ca"]
    assert body["score"]["formula"] and body["score"]["risky_resolved"] == 0


def test_uninspected_remembered_allow_rejected_without_resolving_halt(client, runtime):
    flow = Flow(host="example.test", pid=1, process_key="a" * 64, tls_status="not_inspected")
    task = client.portal.start_task_soon(runtime.halts.hold, flow, 5)

    async def wait_pending():
        async with asyncio.timeout(3):
            while not runtime.halts.pending():
                await asyncio.sleep(0.001)

    client.portal.call(wait_pending)
    pending = client.get("/api/snapshot").json()["pending"]
    assert pending[0]["state"] == "held" and pending[0]["deadline"]
    response = client.post(
        f"/api/halts/{flow.id}/decision", json={"action": "allow", "scope": "always"}
    )
    assert response.status_code == 422
    assert not task.done() and client.get("/api/halts/pending").json()
    assert (
        client.post(f"/api/halts/{flow.id}/decision", json={"action": "block"}).status_code == 200
    )
    assert task.result(timeout=2).action == "block"
