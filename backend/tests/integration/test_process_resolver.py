from types import SimpleNamespace

import psutil

from sentriflow.proxy.process_resolver import ProcessResolver


def test_correct_side_of_loopback_socket(monkeypatch):
    def addr(port):
        return SimpleNamespace(ip="127.0.0.1", port=port)

    monkeypatch.setattr(
        psutil,
        "net_connections",
        lambda **_: [
            SimpleNamespace(laddr=addr(8080), raddr=addr(50000), pid=9),
            SimpleNamespace(laddr=addr(50000), raddr=addr(8080), pid=123),
        ],
    )
    monkeypatch.setattr(
        psutil,
        "Process",
        lambda _: SimpleNamespace(exe=lambda: "C:/test.exe", name=lambda: "test.exe"),
    )
    result = ProcessResolver().resolve("127.0.0.1", 50000, 8080)
    assert result.pid == 123 and len(result.key) == 64


def test_access_denied_is_unknown(monkeypatch):
    def denied(**_):
        raise psutil.AccessDenied()

    monkeypatch.setattr(psutil, "net_connections", denied)
    assert ProcessResolver().resolve("127.0.0.1", 50000, 8080).name == "Unknown"
