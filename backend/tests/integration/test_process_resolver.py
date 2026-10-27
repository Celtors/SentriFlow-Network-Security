from types import SimpleNamespace as NS

import psutil
import pytest

from sentriflow.proxy import process_resolver
from sentriflow.proxy.process_resolver import UNKNOWN_PROCESS, ProcessResolver


@pytest.mark.asyncio
async def test_lookup_cache_and_access_denied(monkeypatch):
    calls = []

    def connections(kind):
        calls.append(kind)
        return [NS(laddr=NS(port=50000), raddr=NS(port=8080), pid=42)]

    monkeypatch.setattr(psutil, "net_connections", connections)
    monkeypatch.setattr(
        psutil, "Process", lambda pid: NS(name=lambda: "browser.exe", exe=lambda: "demo.exe")
    )
    resolver = ProcessResolver()
    assert (await resolver.resolve(50000)).pid == 42
    assert (await resolver.resolve(50000)).name == "browser.exe"
    assert len(calls) == 1
    monkeypatch.setattr(
        psutil, "net_connections", lambda kind: (_ for _ in ()).throw(psutil.AccessDenied())
    )
    assert (await resolver.resolve(50001)).name == UNKNOWN_PROCESS


@pytest.mark.asyncio
async def test_resolves_local_port_to_process(monkeypatch):
    connection = NS(laddr=NS(port=49152), raddr=NS(port=8080), pid=1234)

    class FakeProcess:
        def __init__(self, pid):
            assert pid == 1234

        def name(self):
            return "msedge.exe"

        def exe(self):
            return r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    monkeypatch.setattr(psutil, "net_connections", lambda kind: [connection])
    monkeypatch.setattr(psutil, "Process", FakeProcess)
    result = await ProcessResolver().resolve(49152)
    assert result.pid == 1234
    assert result.name == "msedge.exe"
    assert result.exe_path == r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"


@pytest.mark.asyncio
async def test_access_denied_lists_protected_process(monkeypatch):
    def denied(*, kind):
        raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", denied)
    result = await ProcessResolver().resolve(49152)
    assert result.pid is None
    assert result.name == UNKNOWN_PROCESS


@pytest.mark.asyncio
async def test_process_details_access_denied_keeps_pid_and_hides_executable(monkeypatch):
    connection = NS(laddr=NS(port=49152), raddr=NS(port=8080), pid=1234)

    def denied():
        raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", lambda kind: [connection])
    monkeypatch.setattr(psutil, "Process", lambda pid: NS(name=lambda: "msedge.exe", exe=denied))
    result = await ProcessResolver().resolve(49152)
    assert result.pid == 1234
    assert result.name == "msedge.exe"
    assert result.exe_path is None


@pytest.mark.asyncio
@pytest.mark.parametrize("port", [None, 0, -1, 65536])
async def test_unknown_port_is_not_scanned(monkeypatch, port):
    monkeypatch.setattr(
        psutil,
        "net_connections",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected scan")),
    )
    assert (await ProcessResolver().resolve(port)).name == UNKNOWN_PROCESS


@pytest.mark.asyncio
async def test_protected_identity_remains_unknown_for_decisions(monkeypatch):
    connection = NS(laddr=NS(port=49152), raddr=NS(port=8080), pid=1234)

    def denied():
        raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", lambda kind: [connection])
    monkeypatch.setattr(psutil, "Process", lambda pid: NS(name=denied))
    result = await ProcessResolver().resolve(49152)
    assert result.pid is None
    assert result.name == UNKNOWN_PROCESS


@pytest.mark.asyncio
async def test_resolves_only_connections_to_configured_proxy_port(monkeypatch):
    connections = [
        NS(laddr=NS(port=49152), raddr=NS(port=8080), pid=999),
        NS(laddr=NS(port=49152), raddr=NS(port=8081), pid=1234),
    ]
    monkeypatch.setattr(psutil, "net_connections", lambda kind: connections)
    monkeypatch.setattr(
        psutil, "Process", lambda pid: NS(name=lambda: "msedge.exe", exe=lambda: "")
    )
    result = await ProcessResolver(proxy_port=8081).resolve(49152)
    assert result.pid == 1234
    assert result.exe_path is None


@pytest.mark.asyncio
async def test_cache_expiration(monkeypatch):
    now = [100.0]
    calls = []
    monkeypatch.setattr(process_resolver.time, "monotonic", lambda: now[0])
    resolver = ProcessResolver(cache_ttl=1)
    monkeypatch.setattr(
        resolver, "_lookup", lambda port: calls.append(port) or process_resolver.ProcessInfo()
    )
    await resolver.resolve(49152)
    await resolver.resolve(49152)
    assert calls == [49152]
    now[0] += 2
    await resolver.resolve(49152)
    assert calls == [49152, 49152]


def test_invalid_cache_ttl():
    with pytest.raises(ValueError, match="non-negative"):
        ProcessResolver(cache_ttl=-1)


@pytest.mark.asyncio
async def test_client_address_is_part_of_process_lookup_and_cache(monkeypatch):
    connections = [
        NS(laddr=NS(ip="127.0.0.2", port=49152), raddr=NS(port=8080), pid=2),
        NS(laddr=NS(ip="127.0.0.1", port=49152), raddr=NS(port=8080), pid=1),
    ]
    monkeypatch.setattr(psutil, "net_connections", lambda kind: connections)
    monkeypatch.setattr(
        psutil, "Process", lambda pid: NS(name=lambda: f"app{pid}.exe", exe=lambda: "")
    )
    resolver = ProcessResolver()
    assert (await resolver.resolve(49152, "127.0.0.1")).pid == 1
    assert (await resolver.resolve(49152, "127.0.0.2")).pid == 2
