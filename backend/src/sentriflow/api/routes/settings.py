from fastapi import APIRouter, Request

from sentriflow.core.models import Settings

router = APIRouter()


@router.get("/settings")
async def settings(request: Request):
    return request.app.state.runtime.settings


@router.put("/settings")
async def save_settings(body: Settings, request: Request):
    request.app.state.runtime.set_settings(body)
    return body
