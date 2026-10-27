from sentriflow.core.models import Flow, Rule, Verdict
from sentriflow.core.rule_engine import match_rule


def test_specific_rule_and_block_tie_precedence():
    flow = Flow(host="example.test", process_name="browser.exe", pid=1)
    broad = Rule(process_match="browser.exe", action=Verdict.BLOCK)
    allow = Rule(process_match="browser.exe", host_match="example.test", action=Verdict.ALLOW)
    block = Rule(process_match="browser.exe", host_match="example.test", action=Verdict.BLOCK)
    assert match_rule(flow, [broad, allow]) == allow
    assert match_rule(flow, [allow, block]) == block


def test_wildcard_and_case_boundaries():
    rule = Rule(process_match="Browser.EXE", host_match="*.example.test", action=Verdict.BLOCK)
    assert match_rule(Flow(host="a.EXAMPLE.test.", process_name="browser.exe"), [rule]) == rule
    for host in ["example.test", "notexample.test", "example.test.attacker.test"]:
        assert match_rule(Flow(host=host, process_name="browser.exe"), [rule]) is None


def test_exact_executable_and_host():
    rule = Rule(process_match="a" * 64, host_match="example.test", action=Verdict.BLOCK)
    assert match_rule(Flow(host="example.test", process_key="a" * 64), [rule]) == rule
    assert match_rule(Flow(host="sub.example.test", process_key="a" * 64), [rule]) is None
    assert match_rule(Flow(host="example.test", process_name="a" * 64), [rule]) is None
