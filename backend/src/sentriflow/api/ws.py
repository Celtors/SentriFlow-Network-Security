import asyncio
import secrets

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from sentriflow.api.schemas import HaltCommand
from sentriflow.api.security import valid_host, valid_origin
from sentriflow.application import Runtime
from sentriflow.core.halt_manager import HaltNotFound
from sentriflow.core.models import Verdict, utc_now

router = APIRouter()


@router.websocket("/ws")
async def websocket(socket: WebSocket) -> None:
    rt: Runtime = socket.app.state.runtime
    protocols = socket.scope.get("subprotocols", [])
    if (
        not valid_host(socket.headers, rt.config)
        or not valid_origin(socket.headers, rt.config, required=True)
        or len(protocols) != 2
        or protocols[0] != "sentriflow"
        or not secrets.compare_digest(protocols[1], rt.token)
    ):
        await socket.close(code=1008)
        return
    await socket.accept(subprotocol="sentriflow")

    async def receive() -> None:
        while True:
            try:
                raw = await socket.receive_text()
                if len(raw) > 4096:
                    await socket.close(code=1009)
                    return
                command = HaltCommand.model_validate_json(raw)
                data = command.data
                await rt.halts.resolve(data.id, Verdict(data.action), data.scope)
            except (ValidationError, ValueError):
                await socket.close(code=1008)
                return
            except HaltNotFound:
                # Refresh pending halts after a concurrent/expired decision.
                rt.bus.publish("system.status", {"message": "Halt already resolved or expired"})

    async with rt.bus.subscribe() as queue:

        async def send() -> None:
            await socket.send_json(
                {
                    "type": "system.status",
                    "ts": utc_now().isoformat(),
                    "data": {
                        "proxy_running": rt.proxy_running,
                        "pending_halts": [h.model_dump(mode="json") for h in rt.halts.pending()],
                    },
                }
            )
            while True:
                event = await queue.get()
                if event is None:
                    await socket.close(code=1013)
                    return
                await socket.send_json(event.model_dump(mode="json"))

        tasks = [asyncio.create_task(send()), asyncio.create_task(receive())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
