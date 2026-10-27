from types import SimpleNamespace

from sentriflow.core.models import Flow
from sentriflow.intel.geoip import OfflineGeoIP


def test_missing_and_corrupt_database_are_explicit(tmp_path):
    geo = OfflineGeoIP(tmp_path / "missing.mmdb")
    assert not geo.status()["available"]
    assert geo.lookup("8.8.8.8") is None
    corrupt = tmp_path / "broken.mmdb"
    corrupt.write_bytes(b"not a database")
    assert not OfflineGeoIP(corrupt).status()["available"]


def test_lookup_never_geolocates_private_ips_or_resolves_hosts(tmp_path, monkeypatch):
    calls = []
    geo = OfflineGeoIP(tmp_path / "missing.mmdb")

    def country(address):
        calls.append(address)
        return SimpleNamespace(country=SimpleNamespace(iso_code="US", name="United States"))

    monkeypatch.setattr(geo, "reader", SimpleNamespace(country=country))
    for value in ("127.0.0.1", "192.168.1.2", "::1", "example.test", None):
        assert geo.lookup(value) is None
    assert not calls
    assert geo.lookup("8.8.8.8") == ("US", "United States")
    assert calls == ["8.8.8.8"]


def test_runtime_locates_only_observed_address(runtime, monkeypatch):
    monkeypatch.setattr(runtime.geoip, "lookup", lambda address: ("US", "United States"))
    flow = Flow(host="example.test")
    runtime.locate(flow, "example.test")
    assert flow.destination_ip is None
    assert flow.country_code is None
    runtime.locate(flow, "8.8.8.8")
    assert flow.country_code == "US"
    assert flow.destination_ip == "8.8.8.8"
