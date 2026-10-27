from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from sentriflow.api.dependencies import runtime
from sentriflow.api.schemas import RuleInput
from sentriflow.application import Runtime
from sentriflow.core.models import Rule

router = APIRouter()
RT = Annotated[Runtime, Depends(runtime)]


@router.get("/rules")
async def rules(rt: RT) -> list[Rule]:
    return await rt.rules.list()


@router.post("/rules", status_code=201)
async def create_rule(body: RuleInput, rt: RT) -> Rule:
    rule = await rt.rules.save(Rule(**body.model_dump()))
    rt.bus.publish("rules.updated", {"id": rule.id})
    return rule


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, body: RuleInput, rt: RT) -> Rule:
    existing = next((r for r in await rt.rules.list() if r.id == rule_id), None)
    if not existing:
        raise HTTPException(404, "Rule not found")
    rule = await rt.rules.save(
        Rule(id=rule_id, created_at=existing.created_at, **body.model_dump())
    )
    rt.bus.publish("rules.updated", {"id": rule.id})
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, rt: RT) -> None:
    if not await rt.rules.delete(rule_id):
        raise HTTPException(404, "Rule not found")
    rt.bus.publish("rules.updated", {"id": rule_id})
