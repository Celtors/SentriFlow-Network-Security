from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/flows")
async def flows(
    request: Request,
    limit: int = Query(200, ge=1, le=1000),
    process: str | None = None,
    verdict: str | None = None,
):
    return request.app.state.runtime.flows.list(limit, process, verdict)
