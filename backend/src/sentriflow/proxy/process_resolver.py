import hashlib
import os
import time

import psutil

from sentriflow.core.models import ProcessInfo


class ProcessResolver:
    def __init__(self) -> None:
        self.cache: dict[tuple[str, int, int], tuple[float, ProcessInfo]] = {}

    def resolve(self, host: str, port: int, proxy_port: int) -> ProcessInfo:
        key = (host, port, proxy_port)
        cached = self.cache.get(key)
        if cached and time.monotonic() - cached[0] < 0.5:
            return cached[1]
        try:
            for connection in psutil.net_connections(kind="tcp"):
                if (
                    connection.laddr
                    and connection.raddr
                    and connection.pid
                    and connection.laddr.ip == host
                    and connection.laddr.port == port
                    and connection.raddr.port == proxy_port
                ):
                    process = psutil.Process(connection.pid)
                    path = process.exe()
                    if path:
                        identity = path.casefold() if os.name == "nt" else path
                        result = ProcessInfo(
                            pid=connection.pid,
                            name=process.name(),
                            key=hashlib.sha256(identity.encode()).hexdigest(),
                        )
                        if len(self.cache) >= 1024:
                            self.cache.clear()
                        self.cache[key] = (time.monotonic(), result)
                        return result
        except (psutil.Error, OSError):
            pass
        return ProcessInfo()
