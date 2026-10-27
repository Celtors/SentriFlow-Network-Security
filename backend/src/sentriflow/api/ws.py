import asyncio
import contextlib
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from sentriflow.core.models import Decision, utcnow

router = APIRouter()


@router.websocket("/ws")
async def events(ws: WebSocket):
    runtime, security = ws.app.state.runtime, ws.app.state.security
    if not security.boundary(ws, websocket=True):
        await ws.close(code=1008)
        return
    await ws.accept()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)

    async def receive():
        while True:
            message = await ws.receive_json()
            try:
                if not isinstance(message, dict) or message.get("type") != "halt.decide":
                    raise ValueError("Unsupported WebSocket command")
                body = message["data"]
                runtime.decide(
                    body["id"],
                    Decision.model_validate(
                        {key: value for key, value in body.items() if key != "id"}
                    ),
                )
            except (ValueError, LookupError, KeyError, TypeError):
                if queue.full():
                    queue.get_nowait()
                queue.put_nowait(
                    {
                        "type": "command.error",
                        "ts": utcnow(),
                        "data": {"message": "Invalid or expired decision"},
                    }
                )

    async def send():
        last_snapshot = time.monotonic()
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), 5)
            except TimeoutError:
                event = {"type": "snapshot", "ts": utcnow(), "data": runtime.snapshot()}
            await ws.send_json(event)
            if time.monotonic() - last_snapshot >= 5:
                await ws.send_json({"type": "snapshot", "ts": utcnow(), "data": runtime.snapshot()})
                last_snapshot = time.monotonic()

    tasks = []
    try:
        message = await asyncio.wait_for(ws.receive_json(), 5)
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("token"), str)
            or not security.valid_token(message["token"])
        ):
            await ws.close(code=1008)
            return
        runtime.events.listeners.add(queue)
        await ws.send_json({"type": "snapshot", "ts": utcnow(), "data": runtime.snapshot()})
        tasks = [asyncio.create_task(receive()), asyncio.create_task(send())]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, TimeoutError, ValueError, RuntimeError, json.JSONDecodeError):
        pass
    finally:
        runtime.events.listeners.discard(queue)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect):
                await task
