import re

from sentriflow.core.models import Finding
from sentriflow.inspection.luhn import valid_luhn

EMAIL = re.compile(
    r"[A-Z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Z0-9-]{1,63}"
    r"(?:\.[A-Z0-9-]{1,63}){1,4}",
    re.I,
)
PHONE = re.compile(r"(?<!\w)(?:\+62|62|0)8(?:[ -]?\d){8,11}(?!\d)")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")


def inspect_text(text: str, location: str) -> list[Finding]:
    labels = []
    if "@" in text and EMAIL.search(text):
        labels.append("email")
    if PHONE.search(text):
        labels.append("phone_id")
    if any(valid_luhn(match.group()) for match in CARD.finditer(text)):
        labels.append("payment_card")
    return [Finding(label=label, location=location) for label in labels]
