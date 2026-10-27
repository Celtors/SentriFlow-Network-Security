import ipaddress
import re

from sentriflow.inspection.tracker_matcher import normalize_host


def parse_domains(text: str) -> tuple[set[str], int]:
    """Hosts/plain domains and simple ||domain^ rules only, no Adblock exceptions/modifiers."""
    domains: set[str] = set()
    skipped = 0
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith(("!", "[")):
            continue
        if line.startswith("||"):
            if re.fullmatch(r"\|\|[a-zA-Z0-9.-]+\^", line):
                line = line[2:-1]
            else:
                skipped += 1
                continue
        tokens = line.split()
        if tokens[0] in ("0.0.0.0", "127.0.0.1", "::", "::1"):
            tokens = tokens[1:]
        for token in tokens:
            try:
                host = normalize_host(token)
                if "." not in host:
                    continue
                try:
                    ipaddress.ip_address(host)
                except ValueError:
                    domains.add(host)
            except (ValueError, UnicodeError):
                skipped += 1
    return domains, skipped
