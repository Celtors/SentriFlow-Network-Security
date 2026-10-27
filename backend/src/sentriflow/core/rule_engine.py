from collections.abc import Iterable

from sentriflow.core.models import Flow, Rule


def match_rule(flow: Flow, rules: Iterable[Rule]) -> Rule | None:
    if not flow.process_key:
        return None
    return next(
        (
            rule
            for rule in rules
            if rule.process_match == flow.process_key and rule.host_match == flow.host
        ),
        None,
    )
