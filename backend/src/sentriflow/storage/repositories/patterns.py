from sentriflow.core.models import Pattern


class PatternsRepository:
    """Session-only secrets. No raw sensitive string is persisted in SQLite."""

    def __init__(self) -> None:
        self.items: dict[str, Pattern] = {}

    def save(self, pattern: Pattern) -> None:
        if pattern.is_regex:
            raise ValueError("Regex patterns are not supported; use a literal sensitive string")
        if pattern.id not in self.items and len(self.items) >= 20:
            raise ValueError("At most 20 sensitive strings per session")
        self.items[pattern.id] = pattern

    def delete(self, pattern_id: str) -> bool:
        return self.items.pop(pattern_id, None) is not None

    def public(self) -> list[dict[str, str | bool]]:
        return [pattern.model_dump(exclude={"pattern"}) for pattern in self.items.values()]
