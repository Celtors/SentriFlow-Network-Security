import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sentriflow.core.models import Decision, Flow


class HaltManager:
    def __init__(self, limit: int = 100) -> None:
        self.pending: dict[str, tuple[Flow, asyncio.Future[tuple[Decision, str]]]] = {}
        self.limit = limit
        self.stopping = False

    def check(self, flow_id: str) -> Flow:
        entry = self.pending.get(flow_id)
        if not entry or entry[1].done():
            raise LookupError("Request is no longer pending")
        flow = entry[0]
        if not flow.deadline or datetime.now(UTC) >= datetime.fromisoformat(flow.deadline):
            raise LookupError("Decision deadline expired")
        return flow

    def resolve(self, flow_id: str, decision: Decision) -> None:
        self.check(flow_id)
        self.pending[flow_id][1].set_result((decision, "user"))

    async def hold(
        self, flow: Flow, timeout: float, on_hold: Callable[[Flow], None]
    ) -> tuple[Decision, str]:
        if self.stopping or len(self.pending) >= self.limit:
            return Decision(action="block"), "capacity_or_shutdown"
        future: asyncio.Future[tuple[Decision, str]] = asyncio.get_running_loop().create_future()
        flow.deadline = (datetime.now(UTC) + timedelta(seconds=timeout)).isoformat()
        self.pending[flow.id] = (flow, future)
        try:
            on_hold(flow)
            return await asyncio.wait_for(asyncio.shield(future), timeout)
        except TimeoutError:
            return Decision(action="block"), "timeout"
        finally:
            self.pending.pop(flow.id, None)
            flow.deadline = None
            if not future.done():
                future.cancel()

    def shutdown(self) -> None:
        self.stopping = True
        for _, future in self.pending.values():
            if not future.done():
                future.set_result((Decision(action="block"), "shutdown"))
