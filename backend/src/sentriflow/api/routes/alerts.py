from typing import Annotated

from fastapi import APIRouter, Depends, Query

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime
from sentriflow.core.models import Alert

router = APIRouter()


@router.get("/alerts")
async def alerts(
    rt: Annotated[Runtime, Depends(runtime)],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[Alert]:
    return await rt.alerts.list(limit, offset)
