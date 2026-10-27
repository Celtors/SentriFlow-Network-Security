import pytest

from sentriflow.core.models import Pattern
from sentriflow.inspection.custom_strings import inspect_custom


def test_literals_casefolded_and_not_persisted(runtime):
    pattern = Pattern(label="project_secret", pattern="private-canary")
    runtime.patterns.save(pattern)
    findings = inspect_custom("PRIVATE-CANARY", "body", runtime.patterns.items.values())
    assert findings[0].label == "project_secret"
    assert "private-canary" not in str(runtime.patterns.public())
    assert "private-canary" not in "\n".join(runtime.db.connection.iterdump())
    with pytest.raises(ValueError):
        runtime.patterns.save(Pattern(label="bad", pattern="(a+)+", is_regex=True))
