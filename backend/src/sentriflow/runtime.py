"""Composition root for domain logic, persistence, OS adapters, and event transport."""

import asyncio
import ipaddress
import time
from typing import Any

from sentriflow.config import Config
from sentriflow.core.decision_engine import evaluate
from sentriflow.core.events import EventBus
from sentriflow.core.halt_manager import HaltManager
from sentriflow.core.models import Decision, Finding, Flow, Rule, Settings, Verdict
from sentriflow.core.rule_engine import match_rule
from sentriflow.core.scoring import score
from sentriflow.intel.geoip import OfflineGeoIP
from sentriflow.os_adapters.windows.cert_store import certificate_status
from sentriflow.os_adapters.windows.system_proxy import WindowsProxy
from sentriflow.storage.db import Database
from sentriflow.storage.repositories.alerts import AlertsRepository
from sentriflow.storage.repositories.blocklist import BlocklistRepository
from sentriflow.storage.repositories.flows import FlowsRepository
from sentriflow.storage.repositories.patterns import PatternsRepository
from sentriflow.storage.repositories.rules import RulesRepository
from sentriflow.storage.repositories.settings import SettingsRepository


class Runtime:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.geoip = OfflineGeoIP(config.geoip_database)
        self.db = Database(config.data_dir / "sentriflow.db")
        self.flows = FlowsRepository(self.db)
        self.rules = RulesRepository(self.db)
        self.alerts = AlertsRepository(self.db)
        self.blocklist = BlocklistRepository(self.db)
        self.patterns = PatternsRepository()
        self.settings_repo = SettingsRepository(self.db)
        self.settings = self.settings_repo.get()
        if not self.db.connection.execute("SELECT 1 FROM settings").fetchone():
            self.settings.halt_timeout_seconds = config.halt_timeout_seconds
        self.events = EventBus()
        self.halts = HaltManager()
        self.system_proxy = WindowsProxy(config.data_dir, config.proxy_port)
        self.active: dict[str, Flow] = {}
        self.counters: dict[str, dict[str, Any]] = {}
        self.last_tick = time.monotonic()
        self.proxy_running = False
        self.blocklist.add(
            {"tracker.sentriflow.test", "doubleclick.net", "google-analytics.com"},
            "demo-seed (not a full threat feed)",
        )

    def system_status(self) -> dict[str, Any]:
        return {
            "proxy_running": self.proxy_running,
            "proxy_address": f"127.0.0.1:{self.config.proxy_port}",
            "system_proxy": self.system_proxy.status(),
            "ca": certificate_status(self.config.data_dir / "ca"),
            "capture_scope": "Only HTTP(S) clients routed through this proxy",
        }

    def save(self, flow: Flow, event: str) -> None:
        self.flows.save(flow)
        self.events.publish(event, flow.model_dump(mode="json"))

    def locate(self, flow: Flow, address: str | None) -> None:
        """Use the actual socket peer (or literal destination IP), never a fresh DNS lookup."""
        try:
            flow.destination_ip = str(ipaddress.ip_address(address or ""))
        except ValueError:
            return
        result = self.geoip.lookup(flow.destination_ip)
        flow.country_code = result[0] if result else None

    def held(self, flow: Flow) -> None:
        flow.state = "held"
        self.save(flow, "halt.requested")

    async def inspect_decision(self, flow: Flow) -> Verdict:
        if self.halts.stopping:
            flow.verdict = Verdict.BLOCK
            flow.reason = "Service is stopping"
            flow.state = "completed"
            self.save(flow, "flow.completed")
            return flow.verdict
        if not flow.process_key and flow.bytes_up >= self.settings.unknown_large_bytes:
            flow.findings.append(
                Finding(label="unknown_large_upload", location="process", type="large_upload")
            )
        result = evaluate(flow, match_rule(flow, self.rules.list()), self.settings)
        flow.verdict, flow.reason, flow.verdict_source = (
            result.verdict,
            result.reason,
            result.source,
        )
        self.active[flow.id] = flow
        try:
            if result.verdict == Verdict.HALT:
                decision, source = await self.halts.hold(
                    flow, self.settings.halt_timeout_seconds, self.held
                )
                flow.verdict = Verdict(decision.action)
                flow.verdict_source, flow.reason = source, f"{decision.action.title()} ({source})"
                self.events.publish(
                    "halt.resolved", {"id": flow.id, "action": decision.action, "source": source}
                )
            if flow.verdict == Verdict.BLOCK:
                flow.state = "completed"
                self.finish(flow)
            else:
                flow.state = "started"
                self.record_bytes(flow, up=flow.bytes_up)
                self.save(flow, "flow.started")
            return flow.verdict
        except BaseException:
            self.active.pop(flow.id, None)
            flow.verdict, flow.state = Verdict.BLOCK, "error"
            flow.reason = "Inspection interrupted; blocked locally"
            self.flows.save(flow)
            raise

    def decide(self, flow_id: str, decision: Decision) -> None:
        flow = self.halts.check(flow_id)
        if decision.scope == "always":
            if not flow.process_key:
                raise ValueError("Unknown processes cannot create persistent rules")
            if decision.action == "allow" and flow.tls_status != "inspected":
                raise ValueError("Uninspected requests can only be allowed once")
            self.rules.save(
                Rule(
                    process_match=flow.process_key,
                    process_name=flow.process_name,
                    host_match=flow.host,
                    action=decision.action,
                )
            )
            self.events.publish("rules.updated", {})
        self.halts.resolve(flow_id, decision)

    def record_bytes(self, flow: Flow, up: int = 0, down: int = 0) -> None:
        key = flow.process_key or "unknown"
        counter = self.counters.setdefault(
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

    def download_chunk(self, flow_id: str, size: int) -> None:
        flow = self.active.get(flow_id)
        if flow and flow.verdict == Verdict.ALLOW:
            flow.bytes_down += size
            self.record_bytes(flow, down=size)

    def finish(self, flow: Flow) -> None:
        self.active.pop(flow.id, None)
        flow.state = "error" if flow.state == "error" else "completed"
        self.save(flow, "flow.completed")
        for alert in self.alerts.record(flow):
            self.events.publish("alert.created", alert)
        if flow.findings:
            with self.db.connection:
                self.db.connection.execute(
                    "INSERT OR REPLACE INTO score_events VALUES (?, ?, ?)",
                    (flow.id, int(flow.verdict == Verdict.BLOCK), flow.verdict_source),
                )
            self.events.publish("score.updated", score(self.flows.list(10000)))

    def set_settings(self, settings: Settings) -> None:
        self.settings_repo.save(settings)
        self.settings = settings
        self.events.publish("settings.updated", settings.model_dump())

    def tick(self) -> dict[str, Any]:
        current = time.monotonic()
        elapsed = max(current - self.last_tick, 0.001)
        self.last_tick = current
        rows = []
        for counter in self.counters.values():
            counter["upload_bps"] = counter["interval_up"] / elapsed
            counter["download_bps"] = counter["interval_down"] / elapsed
            counter["interval_up"], counter["interval_down"] = 0, 0
            rows.append({k: v for k, v in counter.items() if not k.startswith("interval_")})
        for flow in list(self.active.values()):
            self.flows.save(flow)
        data = {
            "processes": rows,
            "upload_bps": sum(r["upload_bps"] for r in rows),
            "download_bps": sum(r["download_bps"] for r in rows),
            "elapsed": elapsed,
        }
        self.events.publish("speed.tick", data)
        return data

    async def ticker(self) -> None:
        while not self.halts.stopping:
            await asyncio.sleep(1)
            self.tick()

    def snapshot(self) -> dict[str, Any]:
        # All held flows stay visible even when the recent-history limit is exceeded.
        return {
            "flows": [f.model_dump(mode="json") for f in self.flows.list()],
            "pending": [f.model_dump(mode="json") for f, _ in self.halts.pending.values()],
            "rules": [r.model_dump() for r in self.rules.list()],
            "patterns": self.patterns.public(),
            "alerts": self.alerts.list(),
            "settings": self.settings.model_dump(),
            "score": score(self.flows.list(10000)),
            "blocklist": self.blocklist.status(),
            "system": self.system_status(),
            "processes": [
                {k: v for k, v in c.items() if not k.startswith("interval_")}
                for c in self.counters.values()
            ],
        }
