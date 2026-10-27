from fastapi.testclient import TestClient

from sentriflow.api.server import create_app
from sentriflow.core.models import Flow, Verdict


def test_geo_country_aggregation_and_unknown_counts(runtime, monkeypatch):
    monkeypatch.setattr(runtime.geoip, "status", lambda: {"available": True, "reason": ""})
    monkeypatch.setattr(
        runtime.geoip,
        "lookup",
        lambda address: ("US", "United States") if address == "8.8.8.8" else None,
    )
    for flow in [
        Flow(host="allowed.test", destination_ip="8.8.8.8", bytes_up=100, bytes_down=200),
        Flow(host="blocked.test", destination_ip="8.8.8.8", verdict=Verdict.BLOCK, bytes_up=500),
        Flow(host="localhost", destination_ip="127.0.0.1"),
        Flow(host="held.test"),
        Flow(host="unknown.test", destination_ip="1.1.1.1"),
    ]:
        runtime.flows.save(flow)
    with TestClient(
        create_app(runtime, "test"), base_url="http://127.0.0.1:8787", client=("127.0.0.1", 50000)
    ) as client:
        assert client.get("/api/geo/destinations").status_code == 401
        result = client.get("/api/geo/destinations", headers={"Authorization": "Bearer test"})
    assert result.status_code == 200
    body = result.json()
    assert body["total_requests"] == 5
    assert body["destinations"] == [
        {
            "country_code": "US",
            "country_name": "United States",
            "requests": 2,
            "blocked": 1,
            "bytes_up": 100,
            "bytes_down": 200,
        }
    ]
    assert body["unknown"] == {"no_observed_ip": 1, "local_or_private_ip": 1, "not_in_database": 1}
