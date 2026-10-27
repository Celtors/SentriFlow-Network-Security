from sentriflow.core.models import Finding, Flow, Verdict
from sentriflow.core.scoring import score


def test_transparent_formula_and_caps():
    leak = Flow(host="demo.test", findings=[Finding(type="pii", label="email")])
    blocked = leak.model_copy(update={"verdict": Verdict.BLOCK})
    assert score([leak])["score"] == 90
    assert score([leak, blocked])["score"] == 95
    assert score([blocked] * 50)["score"] == 100
    assert score([leak] * 50)["score"] == 0
