"""Per-flow futures. Waiting for one user never holds up another request."""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Literal, Protocol

from sentriflow.core.events import EventBus
from sentriflow.core.models import Decision, Flow, Halt, Rule, Verdict, utc_now


class RuleWriter(Protocol):
    async def save(self, rule: Rule) -> Rule: ...


class HaltNotFound(Exception):
    pass


@dataclass
class Pending:
    halt: Halt
    future: asyncio.Future[Decision]
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class HaltManager:
    def __init__(self, bus: EventBus, rules: RuleWriter, max_pending: int = 256) -> None:
        self.bus, self.rules, self.max_pending = bus, rules, max_pending
        self._pending: dict[str, Pending] = {}
        self._closed = False

    def pending(self) -> list[Halt]:
        return [p.halt for p in self._pending.values() if not p.future.done()]

    async def hold(self, flow: Flow, timeout: float) -> Decision:
        if self._closed or len(self._pending) >= self.max_pending:
            return Decision(action=Verdict.BLOCK, source="capacity")
        if flow.id in self._pending:
            raise ValueError("Flow is already held")
        deadline = utc_now() + timedelta(seconds=timeout)
        flow.state, flow.deadline = "held", deadline
        pending = Pending(
            Halt(id=flow.id, flow=flow, deadline=deadline),
            asyncio.get_running_loop().create_future(),
        )
        self._pending[flow.id] = pending
        self.bus.publish("halt.requested", pending.halt.model_dump(mode="json"))
        try:
            try:
                decision = await asyncio.wait_for(asyncio.shield(pending.future), timeout)
            except TimeoutError:
                # A decision accepted before the deadline may be committing its saved rule.
                async with pending.lock:
                    decision = (
                        pending.future.result()
                        if pending.future.done()
                        else Decision(action=Verdict.BLOCK, source="timeout")
                    )
            self.bus.publish("halt.resolved", {"id": flow.id, **decision.model_dump(mode="json")})
            return decision
        finally:
            self._pending.pop(flow.id, None)
            if not pending.future.done():
                pending.future.cancel()

    async def resolve(
        self, halt_id: str, action: Verdict, scope: Literal["once", "always"] = "once"
    ) -> Decision:
        if action == Verdict.HALT:
            raise ValueError("A decision must allow or block")
        if scope not in ("once", "always"):
            raise ValueError("Invalid decision scope")
        pending = self._pending.get(halt_id)
        if not pending:
            raise HaltNotFound(halt_id)
        async with pending.lock:
            if pending.future.done() or utc_now() >= pending.halt.deadline:
                raise HaltNotFound(halt_id)
            if (
                scope == "always"
                and action == Verdict.ALLOW
                and pending.halt.flow.tls_status in ("not_inspected", "pinned")
            ):
                raise ValueError("Uninspected requests can only be allowed once")
            rule_id = None
            if scope == "always":
                flow = pending.halt.flow
                # Unknown is not an identity. Never persist a rule for all unknown programs.
                rule = Rule(
                    process_match=flow.process_key
                    or (flow.process_name if flow.pid is not None else None),
                    process_name=flow.process_name
                    if flow.pid is not None or flow.process_key
                    else None,
                    host_match=flow.host,
                    action=action,
                    note="Saved from Halt prompt",
                )
                saved = await self.rules.save(rule)
                rule_id = saved.id
            if pending.future.done():
                raise HaltNotFound(halt_id)
            decision = Decision(action=action, source="user", rule_id=rule_id)
            pending.future.set_result(decision)
            return decision

    def shutdown(self) -> None:
        self._closed = True
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.set_result(Decision(action=Verdict.BLOCK, source="shutdown"))
