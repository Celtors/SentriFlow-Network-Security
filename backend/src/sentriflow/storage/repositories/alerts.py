from sentriflow.core.models import Alert
from sentriflow.storage.db import Database


class AlertRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, alert: Alert) -> None:
        await self.db.execute(
            "INSERT INTO alerts VALUES (?,?,?,?,?,?,?)",
            tuple(alert.model_dump(mode="json").values()),
        )

    async def list(self, limit: int = 100, offset: int = 0) -> list[Alert]:
        return [
            Alert(**r)
            for r in await self.db.fetch(
                "SELECT * FROM alerts ORDER BY ts DESC LIMIT ? OFFSET ?", (limit, offset)
            )
        ]
