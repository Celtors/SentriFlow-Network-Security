import time
from pathlib import Path

import pytest

from sentriflow.inspection.tracker_matcher import TrackerMatcher
from sentriflow.intel.blocklist_loader import (
    clean_domain,
    load_bundled,
    parse_adblock,
    parse_hosts,
)
from sentriflow.storage.db import Database
from sentriflow.storage.repositories.blocklist import BlocklistRepository
from sentriflow.storage.repositories.settings import SettingsRepository

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def db(tmp_path):
    database = Database(tmp_path / "intel.db")
    await database.open()
    yield database
    await database.close()  # Windows: open handle breaks tmp_path cleanup


def test_parse_hosts_keeps_only_real_blocked_domains():
    lines = (FIXTURES / "blocklist_sample.txt").read_text().splitlines()
    assert set(parse_hosts(lines)) == {
        "ads.example.com",
        "tracker.example.net",  # lower-cased, inline comment stripped
        "a.example.org",
        "b.example.org",  # several names on one line
        "metrics.example.com",  # trailing dot stripped
    }


def test_parse_adblock_keeps_only_domain_anchored_rules():
    lines = (FIXTURES / "easyprivacy_sample.txt").read_text().splitlines()
    assert set(parse_adblock(lines)) == {
        "pixel.example.com",
        "beacon.example.net",  # $third-party
        "cdn.example.org",  # $3p
        "stats.example.io",
    }  # no exceptions (@@), paths, wildcards, cosmetic rules, other options, TLDs or localhost


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Ads.Example.COM.", "ads.example.com"),
        ("bücher.example", "xn--bcher-kva.example"),
        ("com", None),  # a bare TLD would block the whole TLD
        ("1.2.3.4", None),
        ("::1", None),
        ("bad..example.com", None),
        ("-bad.example.com", None),
        ("exa mple.com", None),
        ("a" * 64 + ".com", None),
        ("", None),
    ],
)
def test_clean_domain(value, expected):
    assert clean_domain(value) == expected


async def test_replace_source_is_one_fast_transaction(db):
    repo = BlocklistRepository(db)
    domains = {f"host{i}.example.com" for i in range(30_000)}
    start = time.monotonic()
    assert await repo.replace_source("big", domains) == 30_000
    assert time.monotonic() - start < 10  # per-row commits would take minutes
    assert len(await repo.domains()) == 30_000

    assert await repo.replace_source("big", {"only.example.com"}) == 1
    assert await repo.domains() == ["only.example.com"]


async def test_shared_domain_goes_to_the_latest_source(db):
    repo = BlocklistRepository(db)
    await repo.replace_source("a", {"shared.example.com", "a-only.example.com"})
    await repo.replace_source("b", {"shared.example.com"})
    status = {s["source"]: s["count"] for s in await repo.status()}
    assert status == {"a": 1, "b": 1}
    assert sorted(await repo.domains()) == ["a-only.example.com", "shared.example.com"]


def make_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "blocklists"
    directory.mkdir()
    (directory / "stevenblack-hosts.txt").write_bytes(
        (FIXTURES / "blocklist_sample.txt").read_bytes()
    )
    (directory / "easyprivacy.txt").write_bytes((FIXTURES / "easyprivacy_sample.txt").read_bytes())
    return directory


async def test_load_bundled_loads_then_skips_unchanged_then_reloads(db, tmp_path):
    repo, settings = BlocklistRepository(db), SettingsRepository(db)
    directory = make_dir(tmp_path)

    assert await load_bundled(repo, settings, directory) == {"stevenblack": 5, "easyprivacy": 4}
    matcher = TrackerMatcher(await repo.domains())
    assert matcher.matches("deep.sub.ads.example.com")
    assert not matcher.matches("notads.example.com")
    assert not matcher.matches("example.com")

    assert await load_bundled(repo, settings, directory) == {}  # same hash: nothing to do

    (directory / "stevenblack-hosts.txt").write_text("0.0.0.0 fresh.example.com\n")
    assert await load_bundled(repo, settings, directory) == {"stevenblack": 1}
    domains = set(await repo.domains())
    assert "fresh.example.com" in domains and "ads.example.com" not in domains
    assert "pixel.example.com" in domains  # other source untouched


async def test_load_bundled_tolerates_missing_files(db, tmp_path):
    repo, settings = BlocklistRepository(db), SettingsRepository(db)
    assert await load_bundled(repo, settings, tmp_path / "nope") == {}
    assert await repo.domains() == []


async def test_hash_state_does_not_leak_into_editable_settings(db, tmp_path):
    repo, settings = BlocklistRepository(db), SettingsRepository(db)
    await load_bundled(repo, settings, make_dir(tmp_path))
    keys = set(await settings.load())
    assert keys == {"blocklist_sha256:stevenblack", "blocklist_sha256:easyprivacy"}
