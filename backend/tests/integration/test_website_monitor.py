import json
from unittest.mock import AsyncMock

from mitmproxy import connection, http

from sentriflow.core.models import Flow, ProcessInfo, Verdict
from sentriflow.ml.predictor import Predictor
from sentriflow.proxy.addon import SentriFlowAddon
from sentriflow.website.service import MAX_SITES, WebsiteMonitor

NAVIGATION = {"sec-fetch-dest": "document", "sec-fetch-mode": "navigate"}


async def test_live_runtime_inference_events_and_no_sensitive_values(runtime):
    await runtime.open()
    try:
        flow = Flow(host="youtube.com", scheme="https", method="GET")
        url = "https://youtube.com/watch?token=ZZ-private-value"
        async with runtime.bus.subscribe() as events:
            decision = await runtime.inspect(
                flow,
                url,
                {**NAVIGATION, "cookie": "ZZ-private-value", "user-agent": "ZZ-private-value"},
                b"",
            )
            assert decision.action == Verdict.ALLOW
            messages = []
            while not events.empty():
                messages.append((await events.get()).model_dump(mode="json"))
        site = runtime.websites.snapshot()["websites"][0]
        assert site["analysis"] == Predictor().analyze(url)
        assert site["identified_by"] == "page_navigation"
        assert site["evidence"]["cookies"]["state"] == "access_attempt"
        assert any(m["type"] == "website.updated" for m in messages)
        assert "ZZ-private-value" not in json.dumps(messages)
        assert "ZZ-private-value" not in json.dumps(await runtime.snapshot())
        flow.status_code = 200
        runtime.websites.observe_response(flow, {"set-cookie": "ZZ-private-value"})
        await runtime.complete(flow)
        site = runtime.websites.snapshot()["websites"][0]
        assert site["evidence"]["cookies"]["state"] == "transmission_observed"
        assert not site["evidence"]["cookies"]["recipient_access_confirmed"]
        assert "ZZ-private-value" not in json.dumps(site)
    finally:
        await runtime.close()


async def test_background_request_does_not_replace_observed_page(runtime):
    monitor = runtime.websites
    await monitor.open()
    page = Flow(host="example.com", scheme="https", process_key="browser")
    await monitor.observe_request(page, "https://example.com/", NAVIGATION)
    current = monitor.current_id
    resource = Flow(host="cdn.example.net", scheme="https", process_key="browser")
    await monitor.observe_request(
        resource,
        "https://cdn.example.net/script.js",
        {"referer": "https://example.com/private?token=discard"},
    )
    assert monitor.current_id == current
    assert monitor.sites[current]["third_party_requests"] == 1
    assert monitor.sites[current]["external_domains"] == ["cdn.example.net"]
    unrelated = Flow(host="background.example.org", scheme="https", process_key="other")
    await monitor.observe_request(unrelated, "https://background.example.org/", {})
    assert monitor.current_id == current


async def test_missing_model_does_not_break_traffic(runtime, monkeypatch):
    def missing():
        raise FileNotFoundError("private-path-that-must-not-be-logged")

    monkeypatch.setattr("sentriflow.website.service.Predictor", missing)
    await runtime.open()
    try:
        flow = Flow(host="example.com", scheme="https")
        decision = await runtime.inspect(flow, "https://example.com/", NAVIGATION, b"")
        assert decision.action == Verdict.ALLOW
        result = runtime.websites.snapshot()["websites"][0]["analysis"]
        assert result["state"] == "unavailable"
        assert result["maliciousness_percentage"] is None
    finally:
        await runtime.close()


async def test_bounded_site_history(runtime):
    monitor = WebsiteMonitor(runtime.bus)
    for _ in range(MAX_SITES + 5):
        await monitor.observe_request(Flow(host="example.com"), "https://example.com/", NAVIGATION)
    assert len(monitor.sites) == MAX_SITES
    assert monitor.current_id in monitor.sites


async def test_addon_streams_unchanged_html_and_feeds_real_model(runtime):
    await runtime.open()
    runtime.resolver.resolve = AsyncMock(return_value=ProcessInfo(name="test-browser"))
    flow = http.HTTPFlow(
        connection.Client(peername=("127.0.0.1", 50000), sockname=("127.0.0.1", 8080)),
        connection.Server(address=("example.com", 443)),
    )
    flow.request = http.Request.make(
        "GET", "https://example.com/private?token=discard", headers=NAVIGATION
    )
    addon = SentriFlowAddon(runtime)
    body = b'<form action="/submit"><input type="password" value="ZZ-private-value"></form>'
    try:
        await addon.request(flow)
        assert flow.response is None
        flow.response = http.Response.make(200, b"", {"content-type": "text/html"})
        addon.responseheaders(flow)
        assert flow.response.stream(body) == body
        assert flow.response.stream(b"") == b""
        await addon.response(flow)
        site = runtime.websites.snapshot()["websites"][0]
        assert site["analysis"]["state"] == "ready"
        assert site["evidence"]["forms"]["password_fields"] == 1
        assert site["bytes_down"] == len(body)
        assert "ZZ-private-value" not in json.dumps(await runtime.snapshot())
    finally:
        await runtime.close()


def test_website_api_uses_shipped_model_and_existing_auth(client):
    status = client.get("/api/model/status").json()
    assert status["available"] and status["algorithm"] == "random_forest"
    assert client.get("/api/websites").json()["websites"] == []
    assert client.get("/api/websites/missing").status_code == 404
    assert client.get("/api/model/status", headers={"X-SentriFlow-Token": ""}).status_code == 401
