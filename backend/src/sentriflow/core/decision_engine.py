from sentriflow.core.models import Evaluation, Flow, Rule, Settings, Verdict


def evaluate(flow: Flow, rule: Rule | None, settings: Settings) -> Evaluation:
    if rule and rule.action == "block":
        return Evaluation(verdict=Verdict.BLOCK, source="rule", reason="Saved block rule")
    if settings.tracker_mode == "block" and any(f.type == "tracker" for f in flow.findings):
        return Evaluation(verdict=Verdict.BLOCK, source="blocklist", reason="Tracker auto-block")
    if rule and rule.action == "allow" and flow.tls_status == "inspected":
        return Evaluation(verdict=Verdict.ALLOW, source="rule", reason="Saved process/host allow")
    if flow.findings:
        return Evaluation(verdict=Verdict.HALT, source="inspection", reason="Decision required")
    return Evaluation(verdict=Verdict.ALLOW, source="default", reason="No risk detected")
