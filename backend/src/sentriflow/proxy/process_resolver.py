"""Best-effort attribution of a local proxy client port to its owning process."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import psutil

UNKNOWN_PROCESS = "Unknown (protected process)"


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """Process details associated with a proxy client's local TCP port."""

    pid: int | None
    name: str
    exe: str | None = None


class ProcessResolver:
    """Resolve and briefly cache client-port ownership using psutil."""

    def __init__(self, cache_ttl: float = 3.0) -> None:
        if cache_ttl < 0:
            raise ValueError("cache_ttl must be non-negative")
        self._cache_ttl = cache_ttl
        self._cache: dict[int, tuple[float, ProcessInfo]] = {}
        self._lock = threading.Lock()

    def resolve(self, local_port: int | None) -> ProcessInfo:
        """Return the process using ``local_port`` or a safe unknown label."""
        if local_port is None or not 0 < local_port <= 65535:
            return ProcessInfo(pid=None, name=UNKNOWN_PROCESS)

        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(local_port)
            if cached is not None and cached[0] > now:
                return cached[1]

        result = self._lookup(local_port)
        with self._lock:
            self._cache[local_port] = (now + self._cache_ttl, result)
            self._expire(now)
        return result

    def _lookup(self, local_port: int) -> ProcessInfo:
        try:
            connections = psutil.net_connections(kind="tcp")
        except (psutil.AccessDenied, OSError):
            return ProcessInfo(pid=None, name=UNKNOWN_PROCESS)

        pid = next(
            (
                connection.pid
                for connection in connections
                if connection.laddr and connection.laddr.port == local_port
            ),
            None,
        )
        if pid is None:
            return ProcessInfo(pid=None, name=UNKNOWN_PROCESS)

        try:
            process = psutil.Process(pid)
            name = process.name() or UNKNOWN_PROCESS
            try:
                exe = process.exe() or None
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                exe = None
            return ProcessInfo(pid=pid, name=name, exe=exe)
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            return ProcessInfo(pid=pid, name=UNKNOWN_PROCESS)

    def _expire(self, now: float) -> None:
        expired = [port for port, (expires, _) in self._cache.items() if expires <= now]
        for port in expired:
            del self._cache[port]
