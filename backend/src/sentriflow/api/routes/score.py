from fastapi import APIRouter, Request

from sentriflow.core.scoring import score

router = APIRouter()


@router.get("/score")
async def privacy_score(request: Request):
    return score(request.app.state.runtime.flows.list(10000))
