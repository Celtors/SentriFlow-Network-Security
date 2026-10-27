from typing import Annotated, Any

from fastapi import APIRouter, Depends

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime

router = APIRouter()


@router.get("/score")
async def score(rt: Annotated[Runtime, Depends(runtime)]) -> dict[str, Any]:
    return await rt.flows.score()
