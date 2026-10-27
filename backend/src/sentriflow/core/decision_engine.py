from collections.abc import Iterable
from typing import Literal

from sentriflow.core.models import Decision, Flow, Rule, Verdict
from sentriflow.core.rule_engine import match_rule


def evaluate(
    flow: Flow,
    rules: Iterable[Rule],
    *,
    large_upload_bytes: int = 1_048_576,
    tracker_policy: Literal["ask", "block", "alert"] = "ask",
) -> Decision:
    rule = match_rule(flow, rules)
    if rule:
        return Decision(action=rule.action, source="rule", rule_id=rule.id)
    kinds = {finding.type for finding in flow.findings}
    if "tracker" in kinds and tracker_policy == "block":
        return Decision(action=Verdict.BLOCK, source="blocklist")
    if kinds.intersection({"pii", "custom", "inspection_limit"}):
        return Decision(action=Verdict.HALT, source="inspection")
    if "tracker" in kinds and tracker_policy == "ask":
        return Decision(action=Verdict.HALT, source="blocklist")
    if flow.pid is None and flow.bytes_up >= large_upload_bytes:
        return Decision(action=Verdict.HALT, source="large_upload")
    return Decision(action=Verdict.ALLOW, source="default")
