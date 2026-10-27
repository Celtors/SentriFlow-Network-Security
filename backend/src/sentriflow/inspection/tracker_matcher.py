import ipaddress
import re
from collections.abc import Collection


def normalize_host(host: str) -> str:
    host = host.strip().lower().rstrip(".")
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        result = host.encode("idna").decode("ascii")
        if len(result) > 253 or not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
            for label in result.split(".")
        ):
            raise ValueError("Invalid hostname") from None
        return result


def matches_tracker(host: str, domains: Collection[str]) -> bool:
    parts = normalize_host(host).split(".")
    return any(".".join(parts[i:]) in domains for i in range(len(parts)))
