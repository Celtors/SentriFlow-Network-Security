import pytest

from sentriflow.core.events import EventBus


@pytest.mark.asyncio
async def test_slow_subscriber_disconnects_without_blocking_fast_subscriber():
    bus = EventBus(queue_size=1)
    async with bus.subscribe() as slow, bus.subscribe() as fast:
        bus.publish("system.status", {"message": "first"})
        assert (await fast.get()).data["message"] == "first"
        bus.publish("system.status", {"message": "second"})
        assert await slow.get() is None
        assert (await fast.get()).data["message"] == "second"
