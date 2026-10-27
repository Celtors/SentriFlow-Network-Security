import sqlite3

import pytest

from sentriflow.application import Runtime
from sentriflow.core.models import Alert, Flow, Rule, Verdict
from sentriflow.storage.db import Database


@pytest.mark.asyncio
async def test_reopen_filters_and_cascaded_history_clear(runtime):
    await runtime.open()
    flow = Flow(host="demo.test", pid=1, process_name="browser.exe", verdict=Verdict.BLOCK)
    await runtime.flows.save(flow)
    await runtime.alerts.save(
        Alert(
            flow_id=flow.id,
            type="pii",
            severity="high",
            pattern_label="email",
            masked_sample="[redacted]",
        )
    )
    rule = await runtime.rules.save(Rule(host_match="demo.test", action=Verdict.BLOCK))
    await runtime.settings.save({"tracker_policy": "block"})
    await runtime.close()
    fresh = Runtime(runtime.config)
    await fresh.open()
    try:
        assert fresh.config.tracker_policy == "block"
        assert (await fresh.rules.list())[0].id == rule.id
        assert len(await fresh.flows.list(process="browser.exe", verdict="block")) == 1
        assert not await fresh.flows.list(process="missing.exe")
        assert not await fresh.flows.list(process="' OR 1=1 --")
        await fresh.db.execute("DELETE FROM flows")
        assert not await fresh.alerts.list()
        assert len(await fresh.rules.list()) == 1
    finally:
        await fresh.close()


@pytest.mark.asyncio
async def test_newer_database_is_not_downgraded(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA user_version=99")
    db = Database(path)
    with pytest.raises(ValueError, match="newer"):
        await db.open()
    assert db.connection is None
