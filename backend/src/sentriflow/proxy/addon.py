"""Minimal mitmproxy addon used by the Windows proxy spike."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from mitmproxy import http

from sentriflow.proxy.process_resolver import ProcessInfo, ProcessResolver

LOGGER = logging.getLogger("sentriflow.proxy.spike")
Resolver = Callable[[int | None], ProcessInfo]


class ConsoleFlowAddon:
    """Log only destination host and process identity; omit URL and payload."""

    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolve = resolver or ProcessResolver().resolve

    def request(self, flow: http.HTTPFlow) -> None:
        """Log an intercepted HTTP(S) request without its sensitive path/query."""
        peername: Any = flow.client_conn.peername
        source_port = peername[1] if isinstance(peername, tuple) and len(peername) > 1 else None
        process = self._resolve(source_port)
        LOGGER.info(
            "proxy_request method=%s host=%s process=%s pid=%s exe=%s",
            flow.request.method,
            flow.request.pretty_host,
            process.name,
            process.pid if process.pid is not None else "unknown",
            process.exe or "unknown",
        )
