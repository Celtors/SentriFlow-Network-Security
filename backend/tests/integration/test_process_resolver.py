from types import SimpleNamespace as NS

import psutil
import pytest

from sentriflow.proxy.process_resolver import ProcessResolver


@pytest.mark.asyncio
async def test_lookup_cache_and_access_denied(monkeypatch):
    calls = []

    def connections(kind):
        calls.append(kind)
        return [NS(laddr=NS(port=50000), raddr=NS(port=8080), pid=42)]

    monkeypatch.setattr(psutil, "net_connections", connections)
    monkeypatch.setattr(
        psutil,
        "Process",
        lambda pid: NS(pid=pid, name=lambda: "browser.exe", exe=lambda: "demo.exe"),
    )
    resolver = ProcessResolver()
    assert (await resolver.resolve(50000)).pid == 42
    assert (await resolver.resolve(50000)).name == "browser.exe"
    assert len(calls) == 1
    monkeypatch.setattr(
        psutil, "net_connections", lambda kind: (_ for _ in ()).throw(psutil.AccessDenied())
    )
    assert (await resolver.resolve(50001)).name == "Unknown"
