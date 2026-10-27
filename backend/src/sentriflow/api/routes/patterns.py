from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sentriflow.api.dependencies import runtime
from sentriflow.application import Runtime
from sentriflow.core.models import CustomPattern

router = APIRouter()
RT = Annotated[Runtime, Depends(runtime)]


@router.get("/patterns")
async def patterns(rt: RT) -> list[CustomPattern]:
    return await rt.patterns.list()


@router.post("/patterns", status_code=201)
async def create_pattern(body: CustomPattern, rt: RT) -> CustomPattern:
    try:
        return await rt.patterns.save(body)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.put("/patterns/{pattern_id}")
async def update_pattern(pattern_id: str, body: CustomPattern, rt: RT) -> CustomPattern:
    if not any(p.id == pattern_id for p in await rt.patterns.list()):
        raise HTTPException(404, "Pattern not found")
    return await create_pattern(body.model_copy(update={"id": pattern_id}), rt)


@router.delete("/patterns/{pattern_id}", status_code=204)
async def delete_pattern(pattern_id: str, rt: RT) -> None:
    if not await rt.patterns.delete(pattern_id):
        raise HTTPException(404, "Pattern not found")
