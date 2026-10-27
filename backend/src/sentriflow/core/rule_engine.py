"""Exact process matching and domain-boundary matching, with deterministic priority."""

from collections.abc import Iterable

from sentriflow.core.models import Flow, Rule, Verdict


def normalize_host(host: str) -> str:
    return host.rstrip(".").lower().encode("idna").decode("ascii")


def host_matches(host: str, pattern: str) -> bool:
    host, pattern = normalize_host(host), normalize_host(pattern)
    if pattern.startswith("*."):
        suffix = pattern[2:]
        return host != suffix and host.endswith("." + suffix)
    return host == pattern


def match_rule(flow: Flow, rules: Iterable[Rule]) -> Rule | None:
    matches = []
    for rule in rules:
        if rule.action == Verdict.HALT:
            continue
        if rule.process_match and rule.process_match.casefold() != flow.process_name.casefold():
            continue
        if rule.host_match and not host_matches(flow.host, rule.host_match):
            continue
        matches.append(rule)
    # Process+host first; exact host before wildcard; block wins an equal specificity tie.
    return max(
        matches,
        key=lambda r: (
            bool(r.process_match) + bool(r.host_match),
            bool(r.host_match and not r.host_match.startswith("*.")),
            len(r.host_match or ""),
            r.action == Verdict.BLOCK,
            r.created_at,
            r.id,
        ),
        default=None,
    )
