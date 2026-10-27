"""Composition root shared by the proxy and API, on one asyncio loop."""

import asyncio
import secrets
from typing import Any

from sentriflow.config import Settings
from sentriflow.core.decision_engine import evaluate
from sentriflow.core.events import EventBus
from sentriflow.core.halt_manager import HaltManager
from sentriflow.core.models import Alert, Decision, Flow, Verdict
from sentriflow.inspection.pipeline import analyze
from sentriflow.inspection.tracker_matcher import TrackerMatcher
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
        self._speed: dict[str, dict[str, int | str]] = {}

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
        self.started = True

    async def close(self) -> None:
        self.halts.shutdown()
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
        self.bus.publish("flow.started", flow.model_dump(mode="json"))
        if decision.action == Verdict.HALT:
            decision = await self.halts.hold(flow, self.config.halt_timeout_seconds)
        flow.verdict, flow.verdict_source = decision.action, decision.source
        flow.matched_rule_id = decision.rule_id
        return decision

    async def complete(self, flow: Flow) -> None:
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
        speed = self._speed.setdefault(
            flow.process_name, {"process_name": flow.process_name, "bytes_up": 0, "bytes_down": 0}
        )
        if flow.verdict == Verdict.ALLOW:
            speed["bytes_up"] = int(speed["bytes_up"]) + flow.bytes_up
            speed["bytes_down"] = int(speed["bytes_down"]) + flow.bytes_down
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
                    **value,
                    "upload_bps": int(value["bytes_up"]) / interval,
                    "download_bps": int(value["bytes_down"]) / interval,
                }
                for value in self._speed.values()
            ]
            self._speed.clear()
            self.bus.publish("speed.tick", {"interval_seconds": interval, "processes": processes})
            previous = now
