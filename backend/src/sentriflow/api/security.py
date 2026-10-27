import ipaddress
import secrets

from starlette.requests import HTTPConnection


class Security:
    def __init__(self, api_port: int, token: str) -> None:
        self.token = token
        self.hosts = {
            f"{host}:{port}" for host in ("127.0.0.1", "localhost") for port in (api_port, 3000)
        }
        self.origins = {f"http://{host}" for host in self.hosts}

    def boundary(self, connection: HTTPConnection, websocket: bool = False) -> bool:
        try:
            peer_ok = bool(
                connection.client and ipaddress.ip_address(connection.client.host).is_loopback
            )
        except ValueError:
            peer_ok = False
        origin = connection.headers.get("origin")
        return (
            peer_ok
            and connection.headers.get("host") in self.hosts
            and (origin in self.origins if websocket or origin is not None else True)
        )

    def valid_token(self, candidate: str) -> bool:
        return secrets.compare_digest(candidate.encode("utf-8"), self.token.encode("utf-8"))
