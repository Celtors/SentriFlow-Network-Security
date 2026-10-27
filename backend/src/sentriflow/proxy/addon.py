import asyncio
import logging

from mitmproxy import http, tls

from sentriflow.core.models import Finding, Flow, Verdict
from sentriflow.inspection.pipeline import analyze
from sentriflow.inspection.tracker_matcher import normalize_host
from sentriflow.proxy.process_resolver import ProcessResolver
from sentriflow.runtime import Runtime


class GuardianAddon:
    def __init__(self, runtime: Runtime) -> None:
        self.runtime = runtime
        self.resolver = ProcessResolver()

    def running(self) -> None:
        self.runtime.proxy_running = True
        self.runtime.events.publish("system.status", self.runtime.system_status())

    async def request(self, flow: http.HTTPFlow) -> None:
        runtime = self.runtime
        try:
            if flow.request.port in (runtime.config.api_port, 3000) and flow.request.host in (
                "127.0.0.1",
                "localhost",
                "::1",
            ):
                flow.response = http.Response.make(403, b"Dashboard must bypass the proxy.")
                return
            peer = flow.client_conn.peername
            process = await asyncio.to_thread(
                self.resolver.resolve, peer[0], peer[1], runtime.config.proxy_port
            )
            record = Flow(
                id=flow.id,
                host=normalize_host(flow.request.host),
                scheme=flow.request.scheme,
                method=flow.request.method,
                port=flow.request.port,
                pid=process.pid,
                process_name=process.name,
                process_key=process.key,
                bytes_up=len(flow.request.raw_content or b""),
            )
            runtime.locate(record, record.host)
            if flow.request.headers.get("upgrade", "").lower() == "websocket":
                record.findings = [
                    Finding(label="websocket_not_supported", location="protocol", type="inspection")
                ]
                record.verdict, record.state, record.reason = (
                    Verdict.BLOCK,
                    "completed",
                    "WebSocket frame inspection is not supported",
                )
                runtime.finish(record)
                flow.response = http.Response.make(403, b"WebSocket forwarding is not supported.")
                return
            record.findings, inspected = analyze(
                record.host,
                flow.request.pretty_url,
                "\n".join(f"{k}: {v}" for k, v in flow.request.headers.items()),
                flow.request.raw_content or b"",
                flow.request.headers.get("content-type", ""),
                flow.request.headers.get("content-encoding", ""),
                runtime.patterns.items.values(),
                runtime.blocklist.domains(),
                runtime.settings.inspection_enabled,
            )
            record.tls_status = "inspected" if inspected else "not_inspected"
            verdict = await runtime.inspect_decision(record)
            if verdict == Verdict.BLOCK:
                flow.response = http.Response.make(
                    403,
                    b"Blocked locally by SentriFlow.",
                    {"Content-Type": "text/plain", "Cache-Control": "no-store"},
                )
        except asyncio.CancelledError:
            flow.kill()
            raise
        except Exception as exc:
            logging.getLogger("sentriflow").error(
                "Inspection failed (%s); blocked", type(exc).__name__
            )
            flow.response = http.Response.make(503, b"Inspection failed; request blocked locally.")

    def responseheaders(self, flow: http.HTTPFlow) -> None:
        record = self.runtime.active.get(flow.id)
        if not record or record.verdict != Verdict.ALLOW or not flow.response:
            return
        record.status_code = flow.response.status_code
        peer = flow.server_conn.peername
        if peer:
            self.runtime.locate(record, peer[0])

        def count_chunk(chunk: bytes) -> bytes:
            self.runtime.download_chunk(flow.id, len(chunk))
            return chunk

        # Only downstream responses stream. Outbound requests remain buffered for inspection/Halt.
        flow.response.stream = count_chunk

    def response(self, flow: http.HTTPFlow) -> None:
        record = self.runtime.active.get(flow.id)
        if record and flow.response:
            record.status_code = flow.response.status_code
            self.runtime.finish(record)
        elif flow.response and (record := self.runtime.flows.get(flow.id)):
            record.status_code = flow.response.status_code
            self.runtime.flows.save(record)

    def error(self, flow: http.HTTPFlow) -> None:
        record = self.runtime.active.get(flow.id)
        if record:
            record.state = "error"
            record.reason = "Transport error; completion not guaranteed"
            self.runtime.finish(record)

    async def tls_failed_client(self, data: tls.TlsData) -> None:
        try:
            host = data.context.client.sni or (data.context.server.address or (None,))[0]
            if not host:
                return
            peer = data.context.client.peername
            process = await asyncio.to_thread(
                self.resolver.resolve, peer[0], peer[1], self.runtime.config.proxy_port
            )
            record = Flow(
                host=normalize_host(host),
                method="CONNECT",
                pid=process.pid,
                process_name=process.name,
                process_key=process.key,
                tls_status="not_inspected",
                state="error",
                verdict=Verdict.BLOCK,
                verdict_source="tls",
                reason="Encrypted, not inspected: TLS trust or pinning may be the cause",
                findings=[Finding(label="tls_not_inspected", location="tls", type="inspection")],
            )
            self.runtime.finish(record)
        except Exception:
            logging.getLogger("sentriflow").warning("Could not record TLS failure metadata")
