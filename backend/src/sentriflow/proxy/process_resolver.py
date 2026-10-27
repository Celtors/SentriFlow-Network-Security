import asyncio
import time

import psutil

from sentriflow.core.models import ProcessInfo


class ProcessResolver:
    def __init__(self, proxy_port: int = 8080, ttl: float = 1) -> None:
        self.proxy_port, self.ttl = proxy_port, ttl
        self._cache: dict[int, tuple[float, ProcessInfo]] = {}

    async def resolve(self, client_port: int) -> ProcessInfo:
        cached = self._cache.get(client_port)
        if cached and time.monotonic() - cached[0] < self.ttl:
            return cached[1]
        result = await asyncio.to_thread(self._lookup, client_port)
        if len(self._cache) >= 1024:
            self._cache.clear()
        self._cache[client_port] = (time.monotonic(), result)
        return result

    def _lookup(self, client_port: int) -> ProcessInfo:
        try:
            for connection in psutil.net_connections(kind="tcp"):
                if (
                    connection.laddr
                    and connection.laddr.port == client_port
                    and connection.raddr
                    and connection.raddr.port == self.proxy_port
                    and connection.pid
                ):
                    process = psutil.Process(connection.pid)
                    name = process.name()
                    try:
                        exe = process.exe()
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        exe = None
                    return ProcessInfo(pid=process.pid, name=name, exe_path=exe)
        except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
            pass
        return ProcessInfo()
