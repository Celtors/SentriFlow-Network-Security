from typing import Any

from sentriflow.core.rule_engine import normalize_host
from sentriflow.storage.db import Database


class BlocklistRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def domains(self) -> list[str]:
        return [
            r["domain"]
            for r in await self.db.fetch("SELECT domain FROM blocklist_domains WHERE enabled=1")
        ]

    async def add(self, domain: str, source: str = "manual") -> None:
        await self.db.execute(
            "INSERT INTO blocklist_domains VALUES (?,?,1) ON CONFLICT(domain) "
            "DO UPDATE SET enabled=1, source=excluded.source",
            (normalize_host(domain), source),
        )

    async def status(self) -> list[dict[str, Any]]:
        return await self.db.fetch(
            "SELECT source, COUNT(*) AS count, SUM(enabled) AS enabled "
            "FROM blocklist_domains GROUP BY source"
        )
