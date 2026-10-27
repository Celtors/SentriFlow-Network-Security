from sentriflow.core.models import Flow, Rule
from sentriflow.core.rule_engine import match_rule


def test_exact_executable_and_host():
    rule = Rule(process_match="a" * 64, host_match="example.test", action="block")
    assert match_rule(Flow(host="example.test", process_key="a" * 64), [rule]) == rule
    assert match_rule(Flow(host="sub.example.test", process_key="a" * 64), [rule]) is None
    assert match_rule(Flow(host="example.test"), [rule]) is None
