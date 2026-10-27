import pytest

from sentriflow.core.decision_engine import evaluate
from sentriflow.core.models import Finding, Flow, Rule, Verdict


@pytest.mark.parametrize("kind", ["pii", "custom", "inspection_limit"])
def test_sensitive_findings_halt(kind):
    assert (
        evaluate(Flow(host="demo.test", findings=[Finding(type=kind, label="test")]), []).action
        == "halt"
    )


def test_large_unknown_and_small_known():
    assert evaluate(Flow(host="demo.test", bytes_up=1_048_576), []).action == "halt"
    assert evaluate(Flow(host="demo.test", pid=1, bytes_up=100), []).action == "allow"


@pytest.mark.parametrize("policy,action", [("ask", "halt"), ("block", "block"), ("alert", "allow")])
def test_tracker_policy_and_saved_rule(policy, action):
    flow = Flow(host="tracker.test", findings=[Finding(type="tracker", label="tracker")])
    assert evaluate(flow, [], tracker_policy=policy).action == action
    rule = Rule(host_match="tracker.test", action=Verdict.ALLOW)
    assert evaluate(flow, [rule], tracker_policy=policy).source == "rule"
