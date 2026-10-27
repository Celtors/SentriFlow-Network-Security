from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/alerts")
async def alerts(request: Request):
    return request.app.state.runtime.alerts.list()
