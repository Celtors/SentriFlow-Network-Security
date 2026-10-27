import json
import os

import pytest

from sentriflow.os_adapters.windows.system_proxy import WindowsProxy

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows adapter; no real registry writes")


class FakeProxy(WindowsProxy):
    def __init__(self, data_dir, original):
        super().__init__(data_dir, 8080)
        self.values = original.copy()

    def _read(self):
        return self.values.copy()

    def _write(self, values):
        self.values = values.copy()

    def _start_watchdog(self, journal):
        self.watchdog_scheduled = True


def test_snapshot_restore_and_crash_journal(tmp_path, monkeypatch):
    original = {"ProxyEnable": [0, 4], "ProxyServer": None, "ProxyOverride": ["custom.test", 1]}
    adapter = FakeProxy(tmp_path, original)
    adapter.enable()
    assert adapter.watchdog_scheduled
    assert adapter.journal.exists()
    assert adapter.values["ProxyEnable"][0] == 1
    assert adapter.restore()
    assert adapter.values == original
    assert not adapter.journal.exists()
    adapter.enable()
    saved = json.loads(adapter.journal.read_text())
    saved["pid"] = 99999999
    adapter.journal.write_text(json.dumps(saved))
    monkeypatch.setattr(adapter, "owner_alive", lambda _: False)
    assert adapter.restore() and adapter.values == original


def test_watchdog_recovers_dead_owner_without_real_registry(tmp_path, monkeypatch):
    from sentriflow.os_adapters.windows.watchdog import watch

    original = {"ProxyEnable": [0, 4], "ProxyServer": None, "ProxyOverride": None}
    adapter = FakeProxy(tmp_path, original)
    adapter.enable()
    saved = json.loads(adapter.journal.read_text())
    saved["pid"] = 99999999
    adapter.journal.write_text(json.dumps(saved))
    monkeypatch.setattr(adapter, "owner_alive", lambda _: False)
    assert watch(adapter, saved["pid"], saved["created"], 0.001) == 0
    assert adapter.values == original and not adapter.journal.exists()


def test_external_change_is_not_overwritten(tmp_path):
    adapter = FakeProxy(
        tmp_path, {"ProxyEnable": [0, 4], "ProxyServer": None, "ProxyOverride": None}
    )
    adapter.enable()
    adapter.values["ProxyServer"] = ["user-new-proxy:1234", 1]
    with pytest.raises(RuntimeError):
        adapter.restore()
    assert adapter.journal.exists()
