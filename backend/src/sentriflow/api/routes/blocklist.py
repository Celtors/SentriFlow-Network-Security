from typing import Annotated, Any

from fastapi import APIRouter, Depends

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime

router = APIRouter()


@router.get("/blocklist/status")
async def blocklist(rt: Annotated[Runtime, Depends(runtime)]) -> dict[str, Any]:
    return {"sources": await rt.blocklist.status(), "automatic_updates": False}
