"""One event envelope for REST consumers and the dashboard's WebSocket."""

from asyncio import Queue
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from sentriflow.core.models import Model, utc_now

EventType = Literal[
    "flow.started",
    "flow.completed",
    "speed.tick",
    "halt.requested",
    "halt.resolved",
    "alert.created",
    "score.updated",
    "system.status",
]


class Event(Model):
    type: EventType
    ts: datetime = Field(default_factory=utc_now)
    data: dict[str, Any]


class EventBus:
    def __init__(self, queue_size: int = 256) -> None:
        self.queue_size = queue_size
        self._subscribers: set[Queue[Event | None]] = set()

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[Queue[Event | None]]:
        queue: Queue[Event | None] = Queue(self.queue_size)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def publish(self, event_type: EventType, data: dict[str, Any]) -> None:
        event = Event(type=event_type, data=data)
        for queue in tuple(self._subscribers):
            if queue.full():
                # Disconnect lagging clients; on reconnect they fetch pending halts/history.
                self._subscribers.discard(queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(None)
            else:
                queue.put_nowait(event)
