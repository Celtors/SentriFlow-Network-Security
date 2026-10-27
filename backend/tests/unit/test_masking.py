from sentriflow.inspection.masking import masked_sample


def test_mask_never_returns_fragments():
    assert masked_sample("student@example.test") == "[redacted]"
