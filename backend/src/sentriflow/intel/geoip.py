"""Country lookups against a local MMDB. Never resolves DNS or calls a remote service."""

import ipaddress
from pathlib import Path
from typing import Any

import geoip2.database
from geoip2.errors import AddressNotFoundError
from maxminddb import InvalidDatabaseError


class OfflineGeoIP:
    def __init__(self, path: Path):
        self.path = path
        self.reason = "Offline GeoIP database not installed"
        self.reader: geoip2.database.Reader | None = None
        if path.is_file():
            try:
                self.reader = geoip2.database.Reader(str(path))
                self.reason = ""
            except (OSError, ValueError, InvalidDatabaseError):
                self.reason = "Offline GeoIP database could not be opened"

    def lookup(self, address: str | None) -> tuple[str, str] | None:
        if not self.reader or not address:
            return None
        try:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                return None
            country = self.reader.country(str(ip)).country
            code = country.iso_code
            if code and len(code) == 2 and code.isalpha():
                return code.upper(), country.name or code.upper()
        except (ValueError, AddressNotFoundError, OSError, InvalidDatabaseError, TypeError):
            pass
        return None

    def status(self) -> dict[str, Any]:
        return {
            "available": self.reader is not None,
            "reason": self.reason,
            "database": self.path.name,
            "build_epoch": self.reader.metadata().build_epoch if self.reader else None,
            "source": "Local MMDB; DB-IP Lite by default",
            "attribution_url": "https://db-ip.com",
        }

    def close(self) -> None:
        if self.reader:
            self.reader.close()
            self.reader = None
