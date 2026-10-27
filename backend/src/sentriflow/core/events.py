import asyncio
from typing import Any

from sentriflow.core.models import utcnow


class EventBus:
    """Non-blocking, bounded subscribers; snapshots repair dropped events."""

    def __init__(self) -> None:
        self.listeners: set[asyncio.Queue[dict[str, Any]]] = set()

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        event = {"type": event_type, "ts": utcnow(), "data": data}
        for queue in tuple(self.listeners):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)
