from collections.abc import Collection, Iterable
from urllib.parse import unquote_plus

from sentriflow.core.models import Finding, Pattern
from sentriflow.inspection.custom_strings import inspect_custom
from sentriflow.inspection.payload_extractor import MAX_SCAN, decode_body
from sentriflow.inspection.pii_patterns import inspect_text
from sentriflow.inspection.tracker_matcher import matches_tracker


def analyze(
    host: str,
    url: str,
    headers: str,
    body: bytes,
    content_type: str,
    encoding: str,
    patterns: Iterable[Pattern],
    domains: Collection[str],
    enabled: bool = True,
) -> tuple[list[Finding], bool]:
    findings = []
    if matches_tracker(host, domains):
        findings.append(Finding(label="tracker", location="destination", type="tracker"))
    if not enabled:
        return findings, False
    text, complete = decode_body(body, content_type, encoding.lower())
    for location, value in (
        ("url", unquote_plus(url[:MAX_SCAN])),
        ("headers", unquote_plus(headers[:MAX_SCAN])),
        ("body", text),
    ):
        findings.extend(inspect_text(value, location))
        findings.extend(inspect_custom(value, location, patterns))
    if len(url.encode("utf-8")) > MAX_SCAN or len(headers.encode("utf-8")) > MAX_SCAN:
        complete = False
    if not complete:
        findings.append(Finding(label="inspection_incomplete", location="body", type="inspection"))
    return findings, complete
