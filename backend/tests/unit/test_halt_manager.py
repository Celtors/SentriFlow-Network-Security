import asyncio

import pytest

from sentriflow.core.events import EventBus
from sentriflow.core.halt_manager import HaltManager, HaltNotFound
from sentriflow.core.models import Flow, Verdict


class Rules:
    def __init__(self):
        self.saved = []
        self.fail = False

    async def save(self, rule):
        if self.fail:
            raise OSError("storage unavailable")
        self.saved.append(rule)
        return rule


@pytest.mark.asyncio
async def test_default_block_timeout():
    manager = HaltManager(EventBus(), Rules())
    result = await manager.hold(Flow(host="demo.test"), 0.01)
    assert (result.action, result.source) == ("block", "timeout")
    assert manager.pending() == []


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", ["once", "always"])
async def test_user_decision_and_persistence(scope):
    rules = Rules()
    manager = HaltManager(EventBus(), rules)
    flow = Flow(host="demo.test", pid=12, process_name="browser.exe")
    task = asyncio.create_task(manager.hold(flow, 1))
    await asyncio.sleep(0)
    await manager.resolve(flow.id, Verdict.ALLOW, scope)
    assert (await task).source == "user"
    assert len(rules.saved) == (1 if scope == "always" else 0)
    with pytest.raises(HaltNotFound):
        await manager.resolve(flow.id, Verdict.BLOCK)


@pytest.mark.asyncio
async def test_concurrent_resolution_and_independent_flows():
    manager = HaltManager(EventBus(), Rules())
    a, b = Flow(host="a.test"), Flow(host="b.test")
    first, second = asyncio.create_task(manager.hold(a, 1)), asyncio.create_task(manager.hold(b, 1))
    await asyncio.sleep(0)
    results = await asyncio.gather(
        manager.resolve(a.id, Verdict.ALLOW),
        manager.resolve(a.id, Verdict.BLOCK),
        return_exceptions=True,
    )
    assert sum(isinstance(r, HaltNotFound) for r in results) == 1
    assert (await first).action == "allow"
    assert not second.done()
    manager.shutdown()
    assert (await second).source == "shutdown"


@pytest.mark.asyncio
async def test_failed_persistence_does_not_release_and_unknown_rule_is_host_only():
    rules = Rules()
    rules.fail = True
    manager = HaltManager(EventBus(), rules)
    flow = Flow(host="demo.test")
    task = asyncio.create_task(manager.hold(flow, 1))
    await asyncio.sleep(0)
    with pytest.raises(OSError):
        await manager.resolve(flow.id, Verdict.ALLOW, "always")
    assert not task.done()
    rules.fail = False
    await manager.resolve(flow.id, Verdict.BLOCK, "always")
    await task
    assert rules.saved[0].process_match is None


@pytest.mark.asyncio
async def test_capacity_and_cancel_cleanup():
    manager = HaltManager(EventBus(), Rules(), max_pending=1)
    first = asyncio.create_task(manager.hold(Flow(host="a.test"), 1))
    await asyncio.sleep(0)
    assert (await manager.hold(Flow(host="b.test"), 1)).source == "capacity"
    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert not manager.pending()


@pytest.mark.asyncio
async def test_timely_always_decision_waits_for_commit_at_deadline():
    class SlowRules(Rules):
        async def save(self, rule):
            await asyncio.sleep(0.03)
            return await super().save(rule)

    rules = SlowRules()
    manager = HaltManager(EventBus(), rules)
    flow = Flow(host="demo.test")
    task = asyncio.create_task(manager.hold(flow, 0.01))
    await asyncio.sleep(0)
    await manager.resolve(flow.id, Verdict.ALLOW, "always")
    result = await task
    assert result.action == "allow"
    assert result.source == "user"
    assert len(rules.saved) == 1
