from sentriflow.core.models import Finding, Flow, Verdict
from sentriflow.core.scoring import score


def test_score_is_disclosed_ratio_and_no_risks_is_null():
    assert score([])["score"] is None
    findings = [Finding(label="email", location="body")]
    assert (
        score(
            [
                Flow(
                    host="example.test", state="completed", verdict=Verdict.BLOCK, findings=findings
                ),
                Flow(host="example.test", state="completed", findings=findings),
            ]
        )["score"]
        == 50
    )
