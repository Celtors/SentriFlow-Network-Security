from collections.abc import Mapping

from sentriflow.core.models import CustomPattern, Finding
from sentriflow.inspection.custom_strings import inspect_custom
from sentriflow.inspection.payload_extractor import InspectionLimit, extract_parts
from sentriflow.inspection.pii_patterns import inspect_pii
from sentriflow.inspection.tracker_matcher import TrackerMatcher


def analyze(
    host: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    *,
    patterns: list[CustomPattern],
    trackers: TrackerMatcher,
    enabled: bool = True,
) -> list[Finding]:
    findings = []
    if trackers.matches(host):
        findings.append(
            Finding(type="tracker", label="Tracker domain", severity="medium", location="host")
        )
    if not enabled:
        return findings
    try:
        parts = extract_parts(url, headers, body)
    except InspectionLimit as error:
        findings.append(Finding(type="inspection_limit", label=str(error)))
        # URLs and headers still get checked for requests with uninspectable bodies.
        parts = [("url", url[:1_048_576])]
    for location, text in parts:
        findings.extend(inspect_pii(text, location))
        findings.extend(inspect_custom(text, location, patterns))
    return findings
