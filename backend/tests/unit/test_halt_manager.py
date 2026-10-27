import asyncio

import pytest

from sentriflow.core.halt_manager import HaltManager
from sentriflow.core.models import Decision, Finding, Flow, Verdict


async def until_pending(manager, flow_id):
    async with asyncio.timeout(3):
        while flow_id not in manager.pending:
            await asyncio.sleep(0.005)


async def test_timeout_and_duplicate_decisions():
    manager = HaltManager()
    flow = Flow(host="example.test")
    decision, source = await manager.hold(flow, 0.02, lambda _: None)
    assert decision.action == "block" and source == "timeout"
    assert not manager.pending
    with pytest.raises(LookupError):
        manager.resolve(flow.id, Decision(action="allow"))


async def test_concurrent_decisions_and_shutdown():
    manager = HaltManager()
    one, two = Flow(host="one.test"), Flow(host="two.test")
    tasks = [asyncio.create_task(manager.hold(f, 5, lambda _: None)) for f in (one, two)]
    await until_pending(manager, two.id)
    manager.resolve(one.id, Decision(action="allow"))
    manager.shutdown()
    result = await asyncio.gather(*tasks)
    assert [d.action for d, _ in result] == ["allow", "block"]


async def test_always_rules_and_safe_shutdown(runtime):
    flow = Flow(
        host="example.test",
        process_name="demo.exe",
        process_key="a" * 64,
        findings=[Finding(label="email", location="body")],
    )
    task = asyncio.create_task(runtime.inspect_decision(flow))
    await until_pending(runtime.halts, flow.id)
    runtime.decide(flow.id, Decision(action="block", scope="always"))
    assert await task == Verdict.BLOCK
    assert runtime.rules.list()[0].action == "block"
    assert (
        await runtime.inspect_decision(Flow(host="example.test", process_key="a" * 64))
        == Verdict.BLOCK
    )
    assert runtime.alerts.list()[0]["masked_sample"] == "[redacted]"


async def test_unknown_and_uninspected_cannot_remember_allow(runtime):
    flow = Flow(host="example.test", bytes_up=2_000_000)
    task = asyncio.create_task(runtime.inspect_decision(flow))
    await until_pending(runtime.halts, flow.id)
    with pytest.raises(ValueError):
        runtime.decide(flow.id, Decision(action="allow", scope="always"))
    runtime.decide(flow.id, Decision(action="block"))
    await task


async def test_persistence_failure_does_not_leave_orphan_hold(runtime, monkeypatch):
    def fail(_):
        raise OSError("Simulated unavailable disk")

    monkeypatch.setattr(runtime.flows, "save", fail)
    with pytest.raises(OSError):
        await runtime.inspect_decision(
            Flow(host="example.test", findings=[Finding(label="email", location="body")])
        )
    assert not runtime.halts.pending


def test_recovery_restores_held_as_blocked(tmp_path):
    from sentriflow.config import Config
    from sentriflow.runtime import Runtime

    runtime = Runtime(Config(data_dir=tmp_path))
    flow = Flow(host="example.test", state="held", verdict=Verdict.HALT)
    runtime.flows.save(flow)
    runtime.db.close()
    recovered = Runtime(Config(data_dir=tmp_path))
    assert recovered.flows.get(flow.id).verdict == Verdict.BLOCK
    recovered.db.close()
