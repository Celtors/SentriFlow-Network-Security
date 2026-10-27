from sentriflow.inspection.masking import mask_path, mask_sample


def test_all_sensitive_values_are_redacted():
    assert mask_path("/users/alex@example.test?token=secret") == "/[redacted]"
    assert mask_sample("Alex Example") == "[redacted]"
    assert mask_path("/") == "/"
