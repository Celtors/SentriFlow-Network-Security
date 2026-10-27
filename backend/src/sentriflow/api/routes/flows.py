from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime
from sentriflow.core.models import Flow

router = APIRouter()


@router.get("/flows")
async def flows(
    rt: Annotated[Runtime, Depends(runtime)],
    process: str | None = None,
    verdict: Literal["allow", "block", "halt"] | None = None,
    since: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[Flow]:
    return await rt.flows.list(
        process=process,
        verdict=verdict,
        since=since.isoformat() if since else None,
        limit=limit,
        offset=offset,
    )


@router.delete("/flows", status_code=204)
async def clear_flows(rt: Annotated[Runtime, Depends(runtime)]) -> None:
    await rt.db.execute("DELETE FROM flows")
    rt.bus.publish("score.updated", await rt.flows.score())
