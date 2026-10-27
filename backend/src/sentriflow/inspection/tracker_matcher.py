from collections.abc import Iterable

from sentriflow.core.rule_engine import normalize_host


class TrackerMatcher:
    def __init__(self, domains: Iterable[str] = ()) -> None:
        self.domains = {normalize_host(d) for d in domains}

    def matches(self, host: str) -> bool:
        labels = normalize_host(host).split(".")
        return any(".".join(labels[i:]) in self.domains for i in range(len(labels)))
