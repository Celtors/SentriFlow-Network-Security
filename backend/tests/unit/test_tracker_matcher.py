from sentriflow.inspection.tracker_matcher import matches_tracker, normalize_host
from sentriflow.intel.blocklist_loader import parse_domains


def test_suffix_boundary_and_idna():
    assert matches_tracker("sub.TRACKER.test.", {"tracker.test"})
    assert not matches_tracker("nottracker.test", {"tracker.test"})
    assert not matches_tracker("tracker.test.evil.test", {"tracker.test"})
    assert normalize_host("b\u00fccher.test.") == "xn--bcher-kva.test"


def test_hosts_and_supported_adblock_subset():
    domains, skipped = parse_domains(
        "0.0.0.0 tracker.test sub.tracker.test\n||ads.test^\n"
        "@@||exception.test^\n||modifier.test^$script\n127.0.0.1"
    )
    assert domains == {"tracker.test", "sub.tracker.test", "ads.test"}
    assert skipped == 2
