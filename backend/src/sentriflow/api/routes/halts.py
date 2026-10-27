from fastapi import APIRouter, HTTPException, Request

from sentriflow.core.models import Decision

router = APIRouter()


@router.get("/halts/pending")
async def pending(request: Request):
    return [flow for flow, _ in request.app.state.runtime.halts.pending.values()]


@router.post("/halts/{flow_id}/decision")
async def decide(flow_id: str, decision: Decision, request: Request):
    try:
        request.app.state.runtime.decide(flow_id, decision)
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"accepted": True}
