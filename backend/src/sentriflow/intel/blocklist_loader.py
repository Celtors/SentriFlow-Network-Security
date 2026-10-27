"""Parse bundled tracker lists into the blocklist table. Never downloads anything at runtime;
lists are refreshed only by scripts/update-intel.ps1."""

import hashlib
import ipaddress
import re
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

from sentriflow.storage.repositories.blocklist import BlocklistRepository
from sentriflow.storage.repositories.settings import SettingsRepository

LABEL = re.compile(r"^[a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9_])?$")
HOSTS_IPS = {"0.0.0.0", "127.0.0.1"}
HOSTS_SKIP = {"localhost", "localhost.localdomain", "local", "broadcasthost", "0.0.0.0"}
# ||domain^ with no path/wildcard; only the options that keep the rule domain-wide.
ADBLOCK_RULE = re.compile(r"^\|\|([^/*^$|:\s]+)\^(?:\$(?:third-party|3p))?$", re.IGNORECASE)


def clean_domain(value: str) -> str | None:
    """Lower-case, IDNA-encode and validate. Returns None for anything not safe to block."""
    value = value.strip().rstrip(".").lower()
    if not value or len(value) > 253:
        return None
    try:
        ipaddress.ip_address(value)
        return None  # IP literals are not domains
    except ValueError:
        pass
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = value.split(".")
    # A single label would be a bare TLD (e.g. "com") and block everything under it.
    if len(labels) < 2 or not all(LABEL.match(label) for label in labels):
        return None
    return value


def parse_hosts(lines: Iterable[str]) -> Iterator[str]:
    """StevenBlack / hosts format: '0.0.0.0 domain [domain ...]'."""
    for line in lines:
        fields = line.split("#", 1)[0].split()
        if len(fields) < 2 or fields[0] not in HOSTS_IPS:
            continue
        for name in fields[1:]:
            if name.lower() not in HOSTS_SKIP and (domain := clean_domain(name)):
                yield domain


def parse_adblock(lines: Iterable[str]) -> Iterator[str]:
    """EasyPrivacy: only domain-anchored rules. Path rules, wildcards, exceptions (@@) and
    cosmetic rules (##) are out of scope for a domain blocklist."""
    for line in lines:
        match = ADBLOCK_RULE.match(line.strip())
        if match and (domain := clean_domain(match.group(1))):
            yield domain


Parser = Callable[[Iterable[str]], Iterator[str]]
SOURCES: dict[str, tuple[str, Parser]] = {
    "stevenblack": ("stevenblack-hosts.txt", parse_hosts),
    "easyprivacy": ("easyprivacy.txt", parse_adblock),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def load_bundled(
    blocklist: BlocklistRepository, settings: SettingsRepository, directory: Path
) -> dict[str, int]:
    """Load every present list whose file changed since the last load.

    Returns {source: domains_loaded} for the lists that were (re)loaded. The file hash is kept
    in the settings table under 'blocklist_sha256:<source>', which Runtime ignores because it only
    reads the editable settings keys.
    """
    stored = await settings.load()
    counts = {row["source"]: row["count"] for row in await blocklist.status()}
    loaded: dict[str, int] = {}
    for source, (filename, parser) in SOURCES.items():
        path = directory / filename
        if not path.is_file():
            continue
        digest = _sha256(path)
        key = f"blocklist_sha256:{source}"
        if stored.get(key) == digest and counts.get(source):
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            domains = set(parser(handle))
        loaded[source] = await blocklist.replace_source(source, domains)
        await settings.save({key: digest})
    return loaded
