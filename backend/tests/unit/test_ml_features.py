from sentriflow.ml.features import FEATURE_NAMES, extract_features, host_from_url, registered_domain


def test_structural_features_contain_no_secrets():
    values = extract_features("https://user:password@example.com/login?token=private-value")
    assert values is not None and len(values) == len(FEATURE_NAMES)
    assert all(isinstance(value, float) for value in values)
    assert values == extract_features("https://example.com/login?token=private-value")
    assert "password" not in str(values) and "private-value" not in str(values)
    assert values[FEATURE_NAMES.index("https_scheme")] == 1


def test_invalid_features_and_domain_groups():
    for url in ("", "file:///secret", "https://example.com:bad/", "https://", "x" * 8193):
        assert extract_features(url) is None
    assert registered_domain("a.b.example.co.uk") == "example.co.uk"
    assert registered_domain("one.github.io") != registered_domain("two.github.io")
    assert host_from_url("https://EXAMPLE.COM./") == "example.com"
    assert extract_features("http://8.8.8.8/")[5] == 1
