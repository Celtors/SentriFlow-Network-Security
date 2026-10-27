from fastapi import APIRouter, HTTPException, Request

from sentriflow.core.models import Pattern, PatternInput

router = APIRouter()


@router.get("/patterns")
async def patterns(request: Request):
    return request.app.state.runtime.patterns.public()


@router.post("/patterns", status_code=201)
async def add_pattern(body: PatternInput, request: Request):
    item = Pattern(**body.model_dump())
    try:
        request.app.state.runtime.patterns.save(item)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    request.app.state.runtime.events.publish("patterns.updated", {})
    return item.model_dump(exclude={"pattern"})


@router.put("/patterns/{pattern_id}")
async def replace_pattern(pattern_id: str, body: PatternInput, request: Request):
    if pattern_id not in request.app.state.runtime.patterns.items:
        raise HTTPException(404, "Pattern not found")
    item = Pattern(id=pattern_id, **body.model_dump())
    try:
        request.app.state.runtime.patterns.save(item)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    request.app.state.runtime.events.publish("patterns.updated", {})
    return item.model_dump(exclude={"pattern"})


@router.delete("/patterns/{pattern_id}", status_code=204)
async def delete_pattern(pattern_id: str, request: Request):
    if not request.app.state.runtime.patterns.delete(pattern_id):
        raise HTTPException(404, "Pattern not found")
    request.app.state.runtime.events.publish("patterns.updated", {})
