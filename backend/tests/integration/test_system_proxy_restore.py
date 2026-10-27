import copy

import pytest

from sentriflow.os_adapters.windows.system_proxy import NAMES, SystemProxy


class Registry:
    def __init__(self):
        self.values = {
            "ProxyEnable": {"present": True, "value": 0, "type": 4},
            "ProxyServer": {"present": True, "value": "old-proxy.test:8000", "type": 1},
            "ProxyOverride": {"present": False},
        }
        self.refreshes = 0

    def read(self, name):
        return copy.deepcopy(self.values[name])

    def write(self, name, value):
        self.values[name] = copy.deepcopy(value)

    def refresh(self):
        self.refreshes += 1


def test_exact_restore_and_recovery_in_new_process(tmp_path):
    registry = Registry()
    before = copy.deepcopy(registry.values)
    proxy = SystemProxy(tmp_path / "state.json", registry=registry)
    proxy.enable(watchdog=False)
    assert registry.values["ProxyEnable"]["value"] == 1
    assert set(__import__("json").loads(proxy.state_path.read_text())) == set(NAMES)
    with pytest.raises(OSError, match="Saved proxy state"):
        SystemProxy(proxy.state_path, registry=registry).enable(watchdog=False)
    assert SystemProxy(proxy.state_path, registry=registry).restore()
    assert registry.values == before
    assert not proxy.state_path.exists()


def test_partial_enable_rolls_back_and_keeps_state_if_restore_fails(tmp_path):
    registry = Registry()
    original = registry.write

    def fail_on_enable(name, value):
        if name == "ProxyEnable" and value.get("value") == 1:
            raise OSError("write failed")
        original(name, value)

    registry.write = fail_on_enable
    before = copy.deepcopy(registry.values)
    proxy = SystemProxy(tmp_path / "state.json", registry=registry)
    with pytest.raises(OSError):
        proxy.enable(watchdog=False)
    assert registry.values == before
    assert not proxy.state_path.exists()
    registry.write = original
    proxy.enable(watchdog=False)
    registry.refresh = lambda: (_ for _ in ()).throw(OSError("refresh failed"))
    with pytest.raises(OSError):
        proxy.restore()
    assert proxy.state_path.exists()
