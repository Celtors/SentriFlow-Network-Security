from typing import Annotated, Any

from fastapi import APIRouter, Depends

from sentriflow.api.dependencies import runtime
from sentriflow.api.schemas import SettingsInput
from sentriflow.application import EDITABLE_SETTINGS, Runtime
from sentriflow.config import Settings

router = APIRouter()
RT = Annotated[Runtime, Depends(runtime)]


@router.get("/settings")
async def settings(rt: RT) -> dict[str, Any]:
    return rt.config.model_dump(include=EDITABLE_SETTINGS)


@router.put("/settings")
async def update_settings(body: SettingsInput, rt: RT) -> dict[str, Any]:
    values = body.model_dump(exclude_none=True)
    config = Settings.model_validate({**rt.config.model_dump(), **values})
    await rt.settings.save(values)
    rt.config = config
    return await settings(rt)
