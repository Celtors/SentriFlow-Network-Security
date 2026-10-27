from collections.abc import Iterable

from sentriflow.core.models import Flow, Verdict


def score(flows: Iterable[Flow]) -> dict[str, int | None | str]:
    risky = [f for f in flows if f.findings and f.state in ("completed", "error")]
    blocked = sum(f.verdict == Verdict.BLOCK for f in risky)
    return {
        "score": round(100 * blocked / len(risky)) if risky else None,
        "risky_resolved": len(risky),
        "risky_blocked": blocked,
        "formula": "blocked risky requests / resolved risky requests * 100",
        "retention_limit": 10000,
    }
