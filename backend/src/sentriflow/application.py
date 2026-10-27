"""Composition root shared by the proxy and API, on one asyncio loop."""

import asyncio
import ipaddress
import secrets
from typing import Any

from sentriflow.config import Settings
from sentriflow.core.decision_engine import evaluate
from sentriflow.core.events import EventBus
from sentriflow.core.halt_manager import HaltManager
from sentriflow.core.models import Alert, Decision, Flow, Verdict, utc_now
from sentriflow.inspection.pipeline import analyze
from sentriflow.inspection.tracker_matcher import TrackerMatcher
from sentriflow.intel.blocklist_loader import load_bundled
from sentriflow.intel.geoip import OfflineGeoIP
from sentriflow.os_adapters.windows.cert_store import thumbprint
from sentriflow.os_adapters.windows.file_acl import restrict_private_directory
from sentriflow.proxy.process_resolver import ProcessResolver
from sentriflow.storage.db import Database
from sentriflow.storage.repositories.alerts import AlertRepository
from sentriflow.storage.repositories.blocklist import BlocklistRepository
from sentriflow.storage.repositories.flows import FlowRepository
from sentriflow.storage.repositories.patterns import PatternRepository
from sentriflow.storage.repositories.rules import RuleRepository
from sentriflow.storage.repositories.settings import SettingsRepository

EDITABLE_SETTINGS = {
    "inspection_enabled",
    "halt_timeout_seconds",
    "large_upload_bytes",
    "tracker_policy",
}


class Runtime:
    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or Settings()
        self.token = secrets.token_urlsafe(32)
        self.db = Database(self.config.database_path)
        self.flows, self.rules = FlowRepository(self.db), RuleRepository(self.db)
        self.alerts, self.patterns = AlertRepository(self.db), PatternRepository(self.db)
        self.blocklist, self.settings = BlocklistRepository(self.db), SettingsRepository(self.db)
        self.bus = EventBus()
        self.halts = HaltManager(self.bus, self.rules)
        self.resolver = ProcessResolver(self.config.proxy_port)
        self.started = False
        self.proxy_running = False
        self.system_proxy: Any = None
        self.system_lock = asyncio.Lock()
        self.geoip = OfflineGeoIP(self.config.geoip_database)
        self.active: dict[str, Flow] = {}
        self._speed: dict[str, dict[str, Any]] = {}
        self._counted: set[str] = set()

    async def open(self) -> None:
        await asyncio.to_thread(restrict_private_directory, self.config.data_dir)
        await self.db.open()
        persisted = await self.settings.load()
        self.config = Settings.model_validate(
            {
                **self.config.model_dump(),
                **{key: value for key, value in persisted.items() if key in EDITABLE_SETTINGS},
            }
        )
        await load_bundled(
            self.blocklist, self.settings, self.config.geoip_database.parents[1] / "blocklists"
        )
        self.started = True

    async def close(self) -> None:
        self.halts.shutdown()
        self.geoip.close()
        await self.db.close()
        self.started = False

    async def inspect(self, flow: Flow, url: str, headers: dict[str, str], body: bytes) -> Decision:
        flow.findings = await asyncio.to_thread(
            analyze,
            flow.host,
            url,
            headers,
            body,
            patterns=await self.patterns.list(),
            trackers=TrackerMatcher(await self.blocklist.domains()),
            enabled=self.config.inspection_enabled,
        )
        decision = evaluate(
            flow,
            await self.rules.list(),
            large_upload_bytes=self.config.large_upload_bytes,
            tracker_policy=self.config.tracker_policy,
        )
        flow.verdict = decision.action
        if any(f.type == "inspection_limit" for f in flow.findings):
            flow.tls_status = "not_inspected"
        flow.verdict_source = decision.source
        flow.reason = "; ".join(f.label for f in flow.findings) or decision.source
        self.active[flow.id] = flow
        self.bus.publish("flow.started", flow.model_dump(mode="json"))
        if decision.action == Verdict.HALT:
            decision = await self.halts.hold(flow, self.config.halt_timeout_seconds)
        flow.verdict, flow.verdict_source = decision.action, decision.source
        flow.matched_rule_id = decision.rule_id
        flow.state = "started" if flow.verdict == Verdict.ALLOW else "completed"
        flow.deadline = None
        flow.reason = f"{decision.action.value.title()} ({decision.source})"
        if flow.verdict == Verdict.ALLOW:
            self.record_bytes(flow, up=flow.bytes_up)
            self._counted.add(flow.id)
        return decision

    async def complete(self, flow: Flow) -> None:
        self.active.pop(flow.id, None)
        flow.state = "error" if flow.state == "error" else "completed"
        flow.updated_at, flow.deadline = utc_now(), None
        await self.flows.save(flow)
        for finding in flow.findings:
            alert = Alert(
                flow_id=flow.id,
                type=finding.type,
                severity=finding.severity,
                pattern_label=finding.label,
                masked_sample=finding.masked_sample,
            )
            await self.alerts.save(alert)
            self.bus.publish("alert.created", alert.model_dump(mode="json"))
        if flow.verdict == Verdict.ALLOW:
            if flow.id not in self._counted:
                self.record_bytes(flow, up=flow.bytes_up, down=flow.bytes_down)
        self._counted.discard(flow.id)
        self.bus.publish("flow.completed", flow.model_dump(mode="json"))
        self.bus.publish("score.updated", await self.flows.score())

    async def speed_ticker(self) -> None:
        loop = asyncio.get_running_loop()
        previous = loop.time()
        while True:
            await asyncio.sleep(1)
            now = loop.time()
            interval = now - previous
            processes = [
                {
                    **{k: v for k, v in value.items() if not k.startswith("interval_")},
                    "upload_bps": value["interval_up"] / interval,
                    "download_bps": value["interval_down"] / interval,
                }
                for value in self._speed.values()
            ]
            for value, row in zip(self._speed.values(), processes, strict=True):
                value["interval_up"], value["interval_down"] = 0, 0
                value["upload_bps"], value["download_bps"] = row["upload_bps"], row["download_bps"]
            self.bus.publish(
                "speed.tick",
                {
                    "interval_seconds": interval,
                    "elapsed": interval,
                    "processes": processes,
                    "upload_bps": sum(p["upload_bps"] for p in processes),
                    "download_bps": sum(p["download_bps"] for p in processes),
                },
            )
            previous = now

    def record_bytes(self, flow: Flow, *, up: int = 0, down: int = 0) -> None:
        key = flow.process_key or flow.process_name
        counter = self._speed.setdefault(
            key,
            {
                "process_key": flow.process_key,
                "process_name": flow.process_name,
                "bytes_up": 0,
                "bytes_down": 0,
                "upload_bps": 0,
                "download_bps": 0,
                "interval_up": 0,
                "interval_down": 0,
            },
        )
        counter["bytes_up"] += up
        counter["bytes_down"] += down
        counter["interval_up"] += up
        counter["interval_down"] += down

    def download_chunk(self, flow: Flow, size: int) -> None:
        flow.bytes_down += size
        self.record_bytes(flow, down=size)

    def processes(self) -> list[dict[str, Any]]:
        return [
            {k: v for k, v in counter.items() if not k.startswith("interval_")}
            for counter in self._speed.values()
        ]

    def locate(self, flow: Flow, address: str | None) -> None:
        try:
            flow.destination_ip = str(ipaddress.ip_address(address or ""))
        except ValueError:
            return
        country = self.geoip.lookup(flow.destination_ip)
        flow.country_code = country[0] if country else None

    async def system_status(self) -> dict[str, Any]:
        adapter = self.system_proxy
        enabled, server = False, None
        if adapter:
            enabled = bool(
                (await asyncio.to_thread(adapter.registry.read, "ProxyEnable")).get("value")
            )
            server = (await asyncio.to_thread(adapter.registry.read, "ProxyServer")).get("value")
        return {
            "proxy_running": self.proxy_running,
            "proxy_address": f"127.0.0.1:{self.config.proxy_port}",
            "capture_scope": "Only HTTP(S) clients explicitly routed through this proxy",
            "system_proxy": {
                "available": adapter is not None,
                "enabled": enabled,
                "server": server,
                "recovery_pending": (self.config.data_dir / "state.json").exists(),
            },
            "ca": {
                "generated": (self.config.ca_dir / "mitmproxy-ca-cert.pem").exists(),
                "public_certificate": str(self.config.ca_dir / "mitmproxy-ca-cert.cer"),
                "thumbprint": await asyncio.to_thread(thumbprint, self.config.ca_dir),
                "trust_status": "not_checked",
            },
        }

    async def snapshot(self) -> dict[str, Any]:
        records = {flow.id: flow for flow in await self.flows.list(limit=200)}
        records.update(self.active)
        pending = self.halts.pending()
        score = await self.flows.score()
        risk_rows = await self.db.fetch(
            "SELECT COUNT(*) AS total, COALESCE(SUM(verdict='block'),0) AS blocked "
            "FROM flows WHERE verdict IN ('allow','block') AND findings_json != '[]'"
        )
        score.update(risky_resolved=risk_rows[0]["total"], risky_blocked=risk_rows[0]["blocked"])
        alerts = []
        for alert in await self.alerts.list(limit=200):
            flow = records.get(alert.flow_id)
            alerts.append(
                {
                    **alert.model_dump(mode="json"),
                    "host": flow.host if flow else "Unknown",
                    "process_name": flow.process_name if flow else "Unknown",
                }
            )
        return {
            "flows": [
                f.model_dump(mode="json")
                for f in sorted(records.values(), key=lambda f: f.ts, reverse=True)[:200]
            ],
            "pending": [
                {
                    **h.flow.model_dump(mode="json"),
                    "state": "held",
                    "deadline": h.deadline.isoformat(),
                }
                for h in pending
            ],
            "rules": [r.model_dump(mode="json") for r in await self.rules.list()],
            "patterns": [p.model_dump(exclude={"pattern"}) for p in await self.patterns.list()],
            "alerts": alerts,
            "settings": self.config.model_dump(include=EDITABLE_SETTINGS),
            "score": score,
            "blocklist": await self.blocklist.status(),
            "system": await self.system_status(),
            "processes": self.processes(),
        }
