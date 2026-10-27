import secrets
from collections.abc import Mapping

from sentriflow.config import Settings


def valid_host(headers: Mapping[str, str], config: Settings) -> bool:
    return headers.get("host", "").lower() in {
        f"{host}:{port}" for host in ("127.0.0.1", "localhost") for port in (config.api_port, 3000)
    }


def valid_origin(headers: Mapping[str, str], config: Settings, *, required: bool = False) -> bool:
    origin = headers.get("origin")
    if origin is None:
        return not required and headers.get("sec-fetch-site") not in ("cross-site", "same-site")
    return origin in {
        f"http://{host}:{port}"
        for host in ("127.0.0.1", "localhost")
        for port in (config.api_port, 3000)
    }


def tokens_equal(supplied: str, token: str) -> bool:
    # compare_digest(str, str) raises TypeError on non-ASCII input (a 500 instead of a 401).
    return secrets.compare_digest(supplied.encode(), token.encode())


def valid_token(headers: Mapping[str, str], token: str) -> bool:
    supplied = headers.get("x-sentriflow-token", "")
    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        supplied = auth[7:]
    return tokens_equal(supplied, token)
