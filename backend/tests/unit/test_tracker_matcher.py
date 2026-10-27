import pytest

from sentriflow.inspection.tracker_matcher import TrackerMatcher


@pytest.mark.parametrize(
    "host,expected",
    [
        ("tracker.test", True),
        ("a.tracker.test", True),
        ("TRACKER.test.", True),
        ("nottracker.test", False),
        ("tracker.test.attacker.test", False),
    ],
)
def test_domain_boundaries(host, expected):
    assert TrackerMatcher(["tracker.test"]).matches(host) == expected
