import json
from typing import Any

from sentriflow.storage.db import Database


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def load(self) -> dict[str, Any]:
        return {
            r["key"]: json.loads(r["value"]) for r in await self.db.fetch("SELECT * FROM settings")
        }

    async def save(self, settings: dict[str, Any]) -> None:
        for key, value in settings.items():
            await self.db.execute(
                "INSERT INTO settings VALUES (?,?) ON CONFLICT(key) "
                "DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )
