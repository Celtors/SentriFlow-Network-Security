from typing import Annotated, Any

from fastapi import APIRouter, Depends

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime

router = APIRouter()


@router.get("/processes")
async def processes(rt: Annotated[Runtime, Depends(runtime)]) -> list[dict[str, Any]]:
    return await rt.flows.processes()
