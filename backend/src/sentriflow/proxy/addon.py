"""mitmproxy hook boundary; raw request data only lives in memory."""

import asyncio
import inspect
import logging
from collections.abc import Awaitable, Callable

from mitmproxy import http, tls

from sentriflow.application import Runtime
from sentriflow.core.models import Finding, Flow, ProcessInfo, Verdict
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
            if flow.request.host in ("127.0.0.1", "localhost", "::1") and flow.request.port in (
                self.runtime.config.api_port,
                3000,
            ):
                flow.response = http.Response.make(403, b"Dashboard must bypass the proxy.\n")
                return
            process = await self.runtime.resolver.resolve(flow.client_conn.peername[1])
            metadata = Flow(
                id=flow.id,
                pid=process.pid,
                process_name=process.name,
                exe_path=process.exe_path,
                process_key=process.key,
                method=flow.request.method,
                scheme=flow.request.scheme,
                host=flow.request.host,
                port=flow.request.port,
                path_masked=mask_path(flow.request.path),
                bytes_up=len(flow.request.raw_content or b""),
                tls_status=tls_status(flow.request.scheme),
            )
            flow.metadata["sentriflow"] = metadata
            self.runtime.locate(metadata, metadata.host)
            if flow.request.headers.get("upgrade", "").lower() == "websocket":
                metadata.verdict, metadata.verdict_source = Verdict.BLOCK, "unsupported_protocol"
                metadata.reason = "WebSocket frame inspection is not supported"
                metadata.findings = [
                    Finding(type="inspection_limit", label=metadata.reason, location="protocol")
                ]
                flow.response = http.Response.make(403, b"WebSocket forwarding is not supported.\n")
                await self._complete(flow)
                return
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

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        metadata = flow.metadata.get("sentriflow")
        if not metadata or metadata.verdict != Verdict.ALLOW or not flow.response:
            return
        metadata.status_code = flow.response.status_code
        if flow.server_conn.peername:
            self.runtime.locate(metadata, flow.server_conn.peername[0])
        flow.metadata["sentriflow_streamed"] = True

        def count_chunk(chunk: bytes) -> bytes:
            self.runtime.download_chunk(metadata, len(chunk))
            return chunk

        flow.response.stream = count_chunk

    async def error(self, flow: http.HTTPFlow) -> None:
        if metadata := flow.metadata.get("sentriflow"):
            metadata.state = "error"
            metadata.reason = "Transport error; completion not guaranteed"
        await self._complete(flow)

    async def _complete(self, flow: http.HTTPFlow) -> None:
        metadata = flow.metadata.get("sentriflow")
        if not metadata or flow.metadata.get("sentriflow_completed"):
            return
        flow.metadata["sentriflow_completed"] = True
        if flow.response:
            metadata.status_code = flow.response.status_code
        if (
            flow.response
            and metadata.verdict == Verdict.ALLOW
            and not flow.metadata.get("sentriflow_streamed")
        ):
            metadata.bytes_down = len(flow.response.raw_content or b"")
            if flow.id in self.runtime._counted:
                self.runtime.record_bytes(metadata, down=metadata.bytes_down)
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
