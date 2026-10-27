from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/processes")
async def processes(request: Request):
    return request.app.state.runtime.snapshot()["processes"]
