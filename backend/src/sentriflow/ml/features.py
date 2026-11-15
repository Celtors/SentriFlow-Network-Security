"""One versioned extractor shared by training and live inference.

Only numeric structure leaves this boundary. URL/userinfo/query values are never
returned, logged or persisted. HTTPS here means the observed scheme, not trust.
"""

import ipaddress
import math
from collections import Counter
from urllib.parse import urlsplit

import tldextract

FEATURE_VERSION = 1
MAX_URL = 8192
FEATURE_NAMES = (
    "url_length",
    "host_length",
    "path_length",
    "query_length",
    "https_scheme",
    "host_is_ip",
    "subdomain_count",
    "longest_label",
    "tld_length",
    "host_digits",
    "host_digit_ratio",
    "host_hyphens",
    "host_entropy",
    "punycode",
    "path_depth",
    "url_dots",
    "url_hyphens",
    "url_at",
    "url_percent",
    "url_equals",
    "url_ampersands",
    "url_digits",
    "query_parameters",
    "nonstandard_port",
)
# Offline snapshot only; never downloads suffix lists or contacts analyzed sites.
_suffix = tldextract.TLDExtract(
    suffix_list_urls=(), cache_dir=None, include_psl_private_domains=True
)


def host_from_url(url: str) -> str | None:
    if not isinstance(url, str) or not url or len(url) > MAX_URL:
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
            return None
        host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
        _ = parts.port  # Validate malformed/out of range ports too.
        if len(host) > 253 or any(c.isspace() for c in host):
            return None
        return host
    except (ValueError, UnicodeError):
        return None


def registered_domain(host: str) -> str:
    result = _suffix(host)
    return f"{result.domain}.{result.suffix}" if result.suffix else host.lower()


def is_public_host(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return bool(_suffix(host).suffix) and not host.endswith((".local", ".test", ".invalid"))


def extract_features(url: str) -> list[float] | None:
    host = host_from_url(url)
    if host is None:
        return None
    parts = urlsplit(url)
    try:
        ipaddress.ip_address(host)
        is_ip = 1
    except ValueError:
        is_ip = 0
    labels = host.split(".")
    suffix = _suffix(host)
    digits = sum(c.isdigit() for c in host)
    entropy = -sum((n / len(host)) * math.log2(n / len(host)) for n in Counter(host).values())
    # Credentials are discarded before structural URL counts. Query/path strings
    # are transient; values are not decoded, tokenized or handed to the estimator.
    structural = f"{parts.scheme.lower()}://{host}{parts.path}"
    if parts.query:
        structural += "?" + parts.query
    port = parts.port
    values = [
        len(structural),
        len(host),
        len(parts.path),
        len(parts.query),
        int(parts.scheme.lower() == "https"),
        is_ip,
        len(suffix.subdomain.split(".")) if suffix.subdomain else 0,
        max(map(len, labels)),
        len(suffix.suffix),
        digits,
        digits / len(host),
        host.count("-"),
        entropy,
        int("xn--" in host),
        sum(bool(p) for p in parts.path.split("/")),
        structural.count("."),
        structural.count("-"),
        structural.count("@"),
        structural.count("%"),
        structural.count("="),
        structural.count("&"),
        sum(c.isdigit() for c in structural),
        len(parts.query.split("&")) if parts.query else 0,
        int(port is not None and port != (443 if parts.scheme.lower() == "https" else 80)),
    ]
    return [float(value) for value in values]
