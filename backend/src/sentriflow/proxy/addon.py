"""mitmproxy hook boundary; raw request data only lives in memory."""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable

from mitmproxy import http, tls

from sentriflow.application import Runtime
from sentriflow.core.models import Flow, ProcessInfo, Verdict
from sentriflow.inspection.masking import mask_path
from sentriflow.proxy.process_resolver import ProcessResolver
from sentriflow.proxy.tls_status import tls_status

logger = logging.getLogger(__name__)
Resolver = Callable[[int | None], ProcessInfo | Awaitable[ProcessInfo]]


class SentriFlowAddon:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime

    def running(self) -> None:
        self.runtime.proxy_running = True

    def done(self) -> None:
        self.runtime.proxy_running = False

    async def request(self, flow: http.HTTPFlow) -> None:
        try:
            process = await self.runtime.resolver.resolve(flow.client_conn.peername[1])
            metadata = Flow(
                id=flow.id,
                pid=process.pid,
                process_name=process.name,
                exe_path=process.exe_path,
                method=flow.request.method,
                scheme=flow.request.scheme,
                host=flow.request.host,
                port=flow.request.port,
                path_masked=mask_path(flow.request.path),
                bytes_up=len(flow.request.raw_content or b""),
                tls_status=tls_status(flow.request.scheme),
            )
            flow.metadata["sentriflow"] = metadata
            decision = await self.runtime.inspect(
                metadata,
                flow.request.pretty_url,
                {k.lower(): v for k, v in flow.request.headers.items()},
                flow.request.raw_content or b"",
            )
            if decision.action == Verdict.BLOCK:
                flow.response = http.Response.make(
                    403, b"Blocked by SentriFlow\n", {"Content-Type": "text/plain"}
                )
                await self._complete(flow)
        except asyncio.CancelledError:
            flow.kill()
            raise
        except Exception:
            # mitmproxy otherwise logs the hook error and forwards the request.
            logger.error("Request inspection failed; request blocked")
            if metadata := flow.metadata.get("sentriflow"):
                metadata.verdict = Verdict.BLOCK
                metadata.verdict_source = "inspection_error"
            flow.response = http.Response.make(503, b"SentriFlow inspection unavailable\n")

    async def response(self, flow: http.HTTPFlow) -> None:
        await self._complete(flow)

    async def error(self, flow: http.HTTPFlow) -> None:
        await self._complete(flow)

    async def _complete(self, flow: http.HTTPFlow) -> None:
        metadata = flow.metadata.get("sentriflow")
        if not metadata or flow.metadata.get("sentriflow_completed"):
            return
        flow.metadata["sentriflow_completed"] = True
        if flow.response and metadata.verdict == Verdict.ALLOW:
            metadata.bytes_down = len(flow.response.raw_content or b"")
        await self.runtime.complete(metadata)

    async def tls_failed_client(self, data: tls.TlsData) -> None:
        # No inference that failed TLS definitely means pinning. Do not bypass upstream TLS checks.
        client, server = data.context.client, data.context.server
        process = await self.runtime.resolver.resolve(client.peername[1])
        address = server.address or (client.sni or "Unknown", 443)
        await self.runtime.complete(
            Flow(
                id=f"tls-{client.id}",
                host=address[0],
                port=address[1],
                pid=process.pid,
                process_name=process.name,
                exe_path=process.exe_path,
                scheme="https",
                method="CONNECT",
                tls_status="pinned",
                verdict=Verdict.BLOCK,
                verdict_source="tls_error",
            )
        )
        self.runtime.bus.publish(
            "system.status",
            {
                "tls_status": "pinned",
                "message": "Encrypted, not inspected: client TLS failed; "
                "check CA trust or certificate pinning.",
            },
        )


class ConsoleFlowAddon:
    """R1's standalone spike: log destination and identity without request contents."""

    def __init__(self, resolver: Resolver | None = None) -> None:
        self._resolve = resolver or ProcessResolver().resolve

    async def request(self, flow: http.HTTPFlow) -> None:
        peername = flow.client_conn.peername
        source_port = peername[1] if peername and len(peername) > 1 else None
        result = self._resolve(source_port)
        process = await result if inspect.isawaitable(result) else result
        logging.getLogger("sentriflow.proxy.spike").info(
            "proxy_request method=%s host=%s process=%s pid=%s exe=%s",
            flow.request.method,
            flow.request.pretty_host,
            process.name,
            process.pid if process.pid is not None else "unknown",
            process.exe_path or "unknown",
        )
