import pytest

from sentriflow.verification import measure


@pytest.mark.asyncio
async def test_three_real_http_https_rehearsals():
    result = await measure(repetitions=3)
    assert len(result["rehearsals"]) == 3
    assert result["seeded_pii_detection_percent"] == 100
    assert result["decision_max_ms"] < 1000
    assert result["https_inspected"]
    assert result["blocked_payloads_never_reached_upstream"]
