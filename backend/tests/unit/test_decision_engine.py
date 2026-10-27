from sentriflow.core.decision_engine import evaluate
from sentriflow.core.models import Finding, Flow, Rule, Settings, Verdict


def test_precedence_and_incomplete_allow():
    flow = Flow(
        host="example.test",
        process_key="a" * 64,
        findings=[Finding(label="tracker", location="destination", type="tracker")],
    )
    rule = Rule(process_match="a" * 64, host_match="example.test", action="allow")
    assert evaluate(flow, rule, Settings()).verdict == Verdict.ALLOW
    assert evaluate(flow, rule, Settings(tracker_mode="block")).verdict == Verdict.BLOCK
    flow.tls_status = "not_inspected"
    assert evaluate(flow, rule, Settings()).verdict == Verdict.HALT
    rule.action = "block"
    assert evaluate(flow, rule, Settings()).verdict == Verdict.BLOCK
    assert evaluate(Flow(host="safe.test"), None, Settings()).verdict == Verdict.ALLOW
