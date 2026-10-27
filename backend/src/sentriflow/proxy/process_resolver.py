"""Best-effort, nonblocking attribution of a proxy client port to its process."""

import asyncio
import hashlib
import os
import time

import psutil

from sentriflow.constants import UNKNOWN_PROCESS
from sentriflow.core.models import ProcessInfo


class ProcessResolver:
    """Share one process contract between the application and the standalone spike."""

    def __init__(
        self, proxy_port: int = 8080, ttl: float = 1, *, cache_ttl: float | None = None
    ) -> None:
        if not 1 <= proxy_port <= 65535:
            raise ValueError("proxy_port must be between 1 and 65535")
        if cache_ttl is not None:
            ttl = cache_ttl
        if ttl < 0:
            raise ValueError("cache_ttl must be non-negative")
        self.proxy_port, self.ttl = proxy_port, ttl
        self._cache: dict[tuple[str | None, int], tuple[float, ProcessInfo]] = {}

    async def resolve(self, client_port: int | None, client_host: str | None = None) -> ProcessInfo:
        """Resolve off the event loop; invalid or inaccessible ports remain unknown."""
        if client_port is None or not 0 < client_port <= 65535:
            return ProcessInfo(name=UNKNOWN_PROCESS)
        now = time.monotonic()
        key = (client_host, client_port)
        cached = self._cache.get(key)
        if cached and cached[0] > now:
            return cached[1]
        result = (
            await asyncio.to_thread(self._lookup, client_port, client_host)
            if client_host
            else (await asyncio.to_thread(self._lookup, client_port))
        )
        self._expire(time.monotonic())
        if len(self._cache) >= 1024:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = (time.monotonic() + self.ttl, result)
        return result

    def _lookup(self, client_port: int, client_host: str | None = None) -> ProcessInfo:
        try:
            connections = psutil.net_connections(kind="tcp")
        except (psutil.AccessDenied, OSError):
            return ProcessInfo(name=UNKNOWN_PROCESS)
        for connection in connections:
            if not (
                connection.laddr
                and connection.laddr.port == client_port
                and (client_host is None or connection.laddr.ip == client_host)
                and connection.raddr
                and connection.raddr.port == self.proxy_port
                and connection.pid is not None
            ):
                continue
            try:
                process = psutil.Process(connection.pid)
                name = process.name()
                if not name:
                    return ProcessInfo(name=UNKNOWN_PROCESS)
                try:
                    exe = process.exe() or None
                except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                    exe = None
                identity = exe.casefold() if exe and os.name == "nt" else exe
                key = hashlib.sha256(identity.encode()).hexdigest() if identity else None
                return ProcessInfo(pid=connection.pid, name=name, exe_path=exe, key=key)
            except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                # Keep this an unknown identity so large uploads still trigger Halt.
                return ProcessInfo(name=UNKNOWN_PROCESS)
        return ProcessInfo(name=UNKNOWN_PROCESS)

    def _expire(self, now: float) -> None:
        for port in [p for p, (expires, _) in self._cache.items() if expires <= now]:
            del self._cache[port]
