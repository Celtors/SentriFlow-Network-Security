from collections.abc import Iterable

from sentriflow.core.models import Finding, Pattern


def inspect_custom(text: str, location: str, patterns: Iterable[Pattern]) -> list[Finding]:
    # Untrusted regex execution is deliberately not supported in this bounded inspector.
    return [
        Finding(label=pattern.label, location=location)
        for pattern in patterns
        if pattern.enabled
        and not pattern.is_regex
        and pattern.pattern.casefold() in text.casefold()
    ]
