from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sentriflow.api.dependencies import runtime
from sentriflow.api.schemas import DecisionInput
from sentriflow.application import Runtime
from sentriflow.core.halt_manager import HaltNotFound
from sentriflow.core.models import Decision, Halt, Verdict

router = APIRouter()
RT = Annotated[Runtime, Depends(runtime)]


@router.get("/halts/pending")
async def pending(rt: RT) -> list[Halt]:
    return rt.halts.pending()


@router.post("/halts/{halt_id}/decision")
async def decide(halt_id: str, body: DecisionInput, rt: RT) -> Decision:
    try:
        return await rt.halts.resolve(halt_id, Verdict(body.action), body.scope)
    except HaltNotFound as error:
        raise HTTPException(409, "Halt expired, resolved, or not found") from error
