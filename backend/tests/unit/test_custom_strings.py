import pytest

from sentriflow.core.models import CustomPattern
from sentriflow.inspection.custom_strings import inspect_custom, validate_pattern


def test_literal_and_regex():
    findings = inspect_custom(
        "Alex Example ID-123",
        "body",
        [
            CustomPattern(label="name", pattern="alex example"),
            CustomPattern(label="id", pattern=r"ID-\d+", is_regex=True),
            CustomPattern(label="off", pattern="Alex", enabled=False),
        ],
    )
    assert [f.label for f in findings] == ["name", "id"]


def test_regex_validation_and_timeout():
    with pytest.raises(ValueError):
        validate_pattern(CustomPattern(label="bad", pattern="[", is_regex=True))
    findings = inspect_custom(
        "a" * 100_000 + "!",
        "body",
        [CustomPattern(label="nested", pattern=r"(a+)+$", is_regex=True)],
    )
    assert findings[0].type == "inspection_limit"
