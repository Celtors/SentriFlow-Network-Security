"""S18: every /api route is token-, Host- and Origin-protected.

Routes are enumerated from the app itself, so a route added later cannot silently skip auth.
"""

import re

import pytest

EVIL = {
    "origin": {"Origin": "https://attacker.test"},
    "null origin": {"Origin": "null"},
    "wrong host": {"Host": "attacker.test:8787"},
    "wrong host port": {"Host": "127.0.0.1:9999"},
    "cross-site fetch": {"Sec-Fetch-Site": "cross-site"},
}


@pytest.fixture(autouse=True)
def os_calls(monkeypatch):
    """Stub everything that touches the real machine (certificate store, system proxy).

    If the security guard ever breaks, a forged request must not be able to install or remove a
    certificate on the developer's PC while the tests run. Every test also asserts that
    nothing was called.
    """
    calls = []

    def spy(name):
        def fake(*args, **kwargs):
            calls.append(name)
            return {"generated": False, "trusted": False, "thumbprint": None, "supported": True}

        return fake

    monkeypatch.setattr("sentriflow.api.routes.system.install_ca", spy("install_ca"))
    monkeypatch.setattr("sentriflow.api.routes.system.remove_ca", spy("remove_ca"))
    yield calls
    assert calls == [], f"a rejected request reached the OS adapter: {calls}"


def api_operations(client):
    paths = client.app.openapi()["paths"]
    return sorted(
        (method.upper(), re.sub(r"\{[^}]+\}", "x", path))
        for path, operations in paths.items()
        for method in operations
        if path.startswith("/api")
    )


def test_matrix_covers_the_documented_surface(client):
    operations = api_operations(client)
    assert len(operations) >= 22  # Build Plan section 6.2
    assert ("DELETE", "/api/system/ca") in operations
    assert ("POST", "/api/system/proxy") in operations


def test_only_the_dashboard_root_lives_outside_api(client):
    outside = [p for p in client.app.openapi()["paths"] if not p.startswith("/api")]
    assert outside == ["/"], f"unexpected unauthenticated routes: {outside}"


@pytest.mark.parametrize("token", ["", "wrong-token", "café"])
def test_every_api_route_rejects_a_bad_token(client, token):
    for method, path in api_operations(client):
        headers = {"X-SentriFlow-Token": token.encode("latin-1")}
        response = client.request(method, path, headers=headers)
        assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


def test_every_api_route_rejects_missing_token_and_bearer_garbage(client):
    for method, path in api_operations(client):
        for headers in (
            {"X-SentriFlow-Token": ""},
            {"X-SentriFlow-Token": "", "Authorization": "Bearer nope"},
        ):
            response = client.request(method, path, headers=headers)
            assert response.status_code == 401, f"{method} {path} -> {response.status_code}"


@pytest.mark.parametrize("name", EVIL)
def test_every_api_route_rejects_untrusted_origin_or_host_even_with_valid_token(client, name):
    for method, path in api_operations(client):
        response = client.request(method, path, headers=EVIL[name])
        assert response.status_code == 403, f"{name}: {method} {path} -> {response.status_code}"


def test_no_response_carries_cors_headers(client):
    for method, path in api_operations(client):
        attempts = [{"X-SentriFlow-Token": ""}, EVIL["origin"]]
        if method == "GET":  # a valid request must also be CORS-free, but never run a mutation
            attempts.append({})
        for headers in attempts:
            response = client.request(method, path, headers=headers)
            leaked = [h for h in response.headers if h.lower().startswith("access-control-")]
            assert not leaked, f"{method} {path} leaked {leaked}"


def test_rejected_requests_have_no_side_effects(client, runtime, os_calls):
    """A forged request must be stopped before the handler runs (real, valid request bodies)."""
    client.post("/api/system/proxy", json={"enabled": True}, headers={"X-SentriFlow-Token": ""})
    client.post("/api/system/ca", json={"confirmed": True}, headers=EVIL["origin"])
    client.post("/api/system/ca", json={"confirmed": True}, headers={"X-SentriFlow-Token": "bad"})
    client.delete("/api/system/ca", headers=EVIL["null origin"])
    client.delete("/api/flows", headers={"X-SentriFlow-Token": "wrong"})
    client.post(
        "/api/rules", json={"host_match": "x.test", "action": "allow"}, headers=EVIL["null origin"]
    )
    assert os_calls == []
    assert runtime.system_proxy is None
    assert client.get("/api/rules").json() == []


def test_security_headers_are_present(client):
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_token_is_never_echoed(client, runtime):
    for path in ("/api/health", "/api/settings", "/api/system/ca"):
        assert runtime.token not in client.get(path).text
