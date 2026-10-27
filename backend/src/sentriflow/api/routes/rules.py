from fastapi import APIRouter, HTTPException, Request

from sentriflow.core.models import Rule, RuleInput
from sentriflow.inspection.tracker_matcher import normalize_host

router = APIRouter()


@router.get("/rules")
async def rules(request: Request):
    return request.app.state.runtime.rules.list()


@router.post("/rules", status_code=201)
async def save_rule(body: RuleInput, request: Request):
    try:
        rule = Rule(**(body.model_dump() | {"host_match": normalize_host(body.host_match)}))
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(422, "Invalid hostname") from exc
    result = request.app.state.runtime.rules.save(rule)
    request.app.state.runtime.events.publish("rules.updated", {})
    return result


@router.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, request: Request):
    if not request.app.state.runtime.rules.delete(rule_id):
        raise HTTPException(404, "Rule not found")
    request.app.state.runtime.events.publish("rules.updated", {})
