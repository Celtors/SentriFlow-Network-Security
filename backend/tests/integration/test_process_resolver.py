from __future__ import annotations

from types import SimpleNamespace

import psutil

from sentriflow.proxy.process_resolver import UNKNOWN_PROCESS, ProcessResolver


def test_resolves_local_port_to_process(monkeypatch) -> None:
    connection = SimpleNamespace(laddr=SimpleNamespace(port=49152), pid=1234)

    class FakeProcess:
        def __init__(self, pid: int) -> None:
            assert pid == 1234

        def name(self) -> str:
            return "msedge.exe"

        def exe(self) -> str:
            return r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

    monkeypatch.setattr(psutil, "net_connections", lambda kind: [connection])
    monkeypatch.setattr(psutil, "Process", FakeProcess)

    result = ProcessResolver().resolve(49152)

    assert result.pid == 1234
    assert result.name == "msedge.exe"
    assert result.exe == r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"


def test_access_denied_lists_protected_process(monkeypatch) -> None:
    def denied(*, kind: str):
        raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", denied)

    result = ProcessResolver().resolve(49152)

    assert result.pid is None
    assert result.name == UNKNOWN_PROCESS


def test_process_details_access_denied_keeps_pid_and_hides_executable(monkeypatch) -> None:
    connection = SimpleNamespace(laddr=SimpleNamespace(port=49152), pid=1234)

    class FakeProcess:
        def __init__(self, pid: int) -> None:
            pass

        def name(self) -> str:
            return "msedge.exe"

        def exe(self) -> str:
            raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", lambda kind: [connection])
    monkeypatch.setattr(psutil, "Process", FakeProcess)

    result = ProcessResolver().resolve(49152)

    assert result.pid == 1234
    assert result.name == "msedge.exe"
    assert result.exe is None


def test_unknown_port_is_not_scanned(monkeypatch) -> None:
    monkeypatch.setattr(
        psutil,
        "net_connections",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("unexpected scan")),
    )

    assert ProcessResolver().resolve(None).name == UNKNOWN_PROCESS
