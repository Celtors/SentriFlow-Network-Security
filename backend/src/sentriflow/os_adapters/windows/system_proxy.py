"""Opt-in WinINET proxy with durable recovery journal. Never changes proxy at import/startup."""

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import psutil

REGISTRY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
NAMES = ("ProxyEnable", "ProxyServer", "ProxyOverride")


class WindowsProxy:
    def __init__(self, data_dir: Path, port: int) -> None:
        self.journal = data_dir / "state.json"
        self.port = port

    def _read(self) -> dict[str, Any]:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_PATH) as key:
            result = {}
            for name in NAMES:
                try:
                    value, kind = winreg.QueryValueEx(key, name)
                    result[name] = [value, kind]
                except FileNotFoundError:
                    result[name] = None
            return result

    def _write(self, values: dict[str, Any]) -> None:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, REGISTRY_PATH, 0, winreg.KEY_SET_VALUE
        ) as key:
            for name, entry in values.items():
                if entry is None:
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
                else:
                    winreg.SetValueEx(key, name, 0, entry[1], entry[0])
        for option in (39, 37):
            ctypes.windll.wininet.InternetSetOptionW(0, option, 0, 0)

    @staticmethod
    def owner_alive(journal: dict[str, Any]) -> bool:
        try:
            return abs(psutil.Process(journal["pid"]).create_time() - journal["created"]) < 0.01
        except psutil.Error:
            return False

    def enable(self) -> None:
        if os.name != "nt":
            raise RuntimeError("Windows system proxy is unavailable on this platform")
        if self.journal.exists():
            raise RuntimeError("A proxy recovery journal exists; restore it before enabling again")
        import winreg

        applied = {
            "ProxyEnable": [1, winreg.REG_DWORD],
            "ProxyServer": [f"127.0.0.1:{self.port}", winreg.REG_SZ],
            "ProxyOverride": ["localhost;127.0.0.1;<local>", winreg.REG_SZ],
        }
        journal = {
            "original": self._read(),
            "applied": applied,
            "pid": os.getpid(),
            "created": psutil.Process().create_time(),
        }
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.journal.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(journal, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.journal)
        try:
            self._write(applied)
            self._start_watchdog(journal)
        except Exception:
            self._write(journal["original"])
            self.journal.unlink()
            raise

    def _start_watchdog(self, journal: dict[str, Any]) -> None:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "sentriflow.os_adapters.windows.watchdog",
                str(self.journal.parent),
                str(self.port),
                str(journal["pid"]),
                str(journal["created"]),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )

    def restore(self) -> bool:
        if not self.journal.exists():
            return False
        journal = json.loads(self.journal.read_text(encoding="utf-8"))
        if journal["pid"] != os.getpid() and self.owner_alive(journal):
            raise RuntimeError("The session owning these proxy settings is still running")
        current = self._read()
        if any(
            current.get(name) not in (journal["applied"].get(name), journal["original"].get(name))
            for name in NAMES
        ):
            raise RuntimeError("Proxy settings changed externally; recovery journal preserved")
        self._write(journal["original"])
        self.journal.unlink()
        return True

    def status(self) -> dict[str, Any]:
        state: dict[str, Any] = {
            "available": os.name == "nt",
            "recovery_pending": self.journal.exists(),
        }
        if os.name == "nt":
            values = self._read()
            state["enabled"] = bool(values.get("ProxyEnable") and values["ProxyEnable"][0])
            state["server"] = values["ProxyServer"][0] if values.get("ProxyServer") else None
        return state
