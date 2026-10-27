from collections.abc import Iterable
from typing import Any

from sentriflow.core.models import Flow, Verdict


def score(flows: Iterable[Flow]) -> dict[str, Any]:
    breakdown = {"blocked_pii": 0, "allowed_pii": 0, "blocked_tracker": 0, "allowed_tracker": 0}
    for flow in flows:
        kinds = {f.type for f in flow.findings}
        prefix = "blocked" if flow.verdict == Verdict.BLOCK else "allowed"
        if kinds.intersection({"pii", "custom"}):
            breakdown[prefix + "_pii"] += 1
        if "tracker" in kinds:
            breakdown[prefix + "_tracker"] += 1
    weights = {"blocked_pii": 5, "allowed_pii": -10, "blocked_tracker": 1, "allowed_tracker": -2}
    delta = sum(count * weights[key] for key, count in breakdown.items())
    return {
        "score": min(100, max(0, 100 + delta)),
        "breakdown": breakdown,
        "weights": weights,
        "formula": "clamp(100 + 5*blocked_pii - 10*allowed_pii + blocked_tracker "
        "- 2*allowed_tracker, 0, 100)",
    }
