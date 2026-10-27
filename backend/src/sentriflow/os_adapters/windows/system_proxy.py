"""Per-user WinINET routing, exact restoration, and an independent crash watchdog."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import psutil

from sentriflow.os_adapters.base import Registry

KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
NAMES = ("ProxyEnable", "ProxyServer", "ProxyOverride")


class WindowsRegistry:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise OSError("Windows system proxy is only available on Windows")
        import winreg

        self.winreg = winreg

    def read(self, name: str) -> dict[str, Any]:
        w = self.winreg
        with w.OpenKey(w.HKEY_CURRENT_USER, KEY) as key:
            try:
                value, kind = w.QueryValueEx(key, name)
                return {"present": True, "value": value, "type": kind}
            except FileNotFoundError:
                return {"present": False}

    def write(self, name: str, value: dict[str, Any]) -> None:
        w = self.winreg
        with w.OpenKey(w.HKEY_CURRENT_USER, KEY, 0, w.KEY_SET_VALUE) as key:
            if value["present"]:
                w.SetValueEx(key, name, 0, value["type"], value["value"])
            else:
                try:
                    w.DeleteValue(key, name)
                except FileNotFoundError:
                    pass

    def refresh(self) -> None:
        import ctypes

        internet = ctypes.WinDLL("wininet", use_last_error=True)
        for option in (39, 37):  # INTERNET_OPTION_SETTINGS_CHANGED / REFRESH
            if not internet.InternetSetOptionW(None, option, None, 0):
                raise ctypes.WinError(ctypes.get_last_error())


class SystemProxy:
    def __init__(
        self, state_path: Path, port: int = 8080, registry: Registry | None = None
    ) -> None:
        self.state_path, self.port = state_path, port
        self.registry = registry or WindowsRegistry()
        self.enabled = False

    def enable(self, *, watchdog: bool = True) -> None:
        if self.enabled:
            return
        if self.state_path.exists():
            raise OSError("Saved proxy state exists; run sentriflow restore-proxy first")
        state = {name: self.registry.read(name) for name in NAMES}
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_name(f".proxy-{uuid4()}.tmp")
        try:
            with temporary.open("x", encoding="utf-8") as file:
                json.dump(state, file)
                file.flush()
                os.fsync(file.fileno())
            # Atomically publish a complete snapshot and refuse to replace another session's state.
            os.link(temporary, self.state_path)
        finally:
            temporary.unlink(missing_ok=True)
        try:
            if watchdog:
                self._start_watchdog()
            for name, value, kind in (
                ("ProxyServer", f"127.0.0.1:{self.port}", 1),
                ("ProxyOverride", "<local>;localhost;127.*;[::1]", 1),
                ("ProxyEnable", 1, 4),
            ):
                self.registry.write(name, {"present": True, "value": value, "type": kind})
            self.registry.refresh()
            self.enabled = True
        except BaseException:
            self.restore()
            raise

    def restore(self) -> bool:
        if not self.state_path.exists():
            self.enabled = False
            return False
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if set(state) != set(NAMES):
            raise OSError("Invalid proxy recovery state; leaving snapshot intact")
        # Delete the recovery file only after all writes and notifications succeed.
        for name in NAMES:
            self.registry.write(name, state[name])
        self.registry.refresh()
        self.state_path.unlink(missing_ok=True)
        self.enabled = False
        return True

    def _start_watchdog(self) -> None:
        command = [
            sys.executable,
            "-m",
            "sentriflow.os_adapters.windows.system_proxy",
            "--watch",
            str(os.getpid()),
            "--started",
            str(psutil.Process().create_time()),
            "--state",
            str(self.state_path),
        ]
        flags = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32"
            else 0
        )
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=True,
        )


def watch(parent_pid: int, started: float, state_path: Path) -> None:
    while state_path.exists():
        try:
            parent = psutil.Process(parent_pid)
            if parent.create_time() != started or not parent.is_running():
                break
        except psutil.NoSuchProcess:
            break
        time.sleep(1)
    if state_path.exists():
        SystemProxy(state_path).restore()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", type=int, required=True)
    parser.add_argument("--started", type=float, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    watch(args.watch, args.started, args.state)
