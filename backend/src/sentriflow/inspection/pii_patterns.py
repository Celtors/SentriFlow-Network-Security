import regex as re

from sentriflow.core.models import Finding
from sentriflow.inspection.luhn import is_valid_card

EMAIL = re.compile(r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9-]+(?:\.[A-Z0-9-]+)+", re.I)
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
PHONE = re.compile(r"(?<!\w)(?:\+62|62|0)8\d(?:[ -]?\d){7,10}(?!\d)")


def inspect_pii(text: str, location: str) -> list[Finding]:
    findings = []
    try:
        for label, matched in (
            ("Email address", EMAIL.search(text, timeout=0.02) is not None),
            (
                "Payment card (Luhn)",
                any(is_valid_card(m.group()) for m in CARD.finditer(text, timeout=0.02)),
            ),
            ("Indonesian mobile number", PHONE.search(text, timeout=0.02) is not None),
        ):
            if matched:
                findings.append(Finding(type="pii", label=label, location=location))
    except TimeoutError:
        findings.append(
            Finding(type="inspection_limit", label="PII inspection timed out", location=location)
        )
    return findings
