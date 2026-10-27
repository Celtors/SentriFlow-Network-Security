import regex

from sentriflow.core.models import CustomPattern, Finding


def validate_pattern(pattern: CustomPattern) -> None:
    if pattern.is_regex:
        try:
            regex.compile(pattern.pattern)
        except regex.error as error:
            raise ValueError("Invalid regular expression") from error


def inspect_custom(text: str, location: str, patterns: list[CustomPattern]) -> list[Finding]:
    findings = []
    for pattern in patterns:
        if not pattern.enabled:
            continue
        try:
            matched = (
                regex.search(pattern.pattern, text, timeout=0.02) is not None
                if pattern.is_regex
                else pattern.pattern.casefold() in text.casefold()
            )
        except TimeoutError:
            findings.append(
                Finding(
                    type="inspection_limit", label="Pattern inspection timed out", location=location
                )
            )
            continue
        if matched:
            findings.append(Finding(type="custom", label=pattern.label, location=location))
    return findings
