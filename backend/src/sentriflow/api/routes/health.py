from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    return {"ok": True, "version": "0.1.0", **request.app.state.runtime.system_status()}


@router.get("/snapshot")
async def snapshot(request: Request):
    return request.app.state.runtime.snapshot()
