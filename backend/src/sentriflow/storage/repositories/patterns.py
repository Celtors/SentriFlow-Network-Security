from sentriflow.core.models import CustomPattern
from sentriflow.inspection.custom_strings import validate_pattern
from sentriflow.storage.db import Database


class PatternRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def list(self) -> list[CustomPattern]:
        return [CustomPattern(**r) for r in await self.db.fetch("SELECT * FROM custom_patterns")]

    async def save(self, pattern: CustomPattern) -> CustomPattern:
        validate_pattern(pattern)
        await self.db.execute(
            "INSERT INTO custom_patterns VALUES (?,?,?,?,?) ON CONFLICT(id) "
            "DO UPDATE SET label=excluded.label, pattern=excluded.pattern, "
            "is_regex=excluded.is_regex, enabled=excluded.enabled",
            tuple(pattern.model_dump().values()),
        )
        return pattern

    async def delete(self, pattern_id: str) -> bool:
        return bool(await self.db.execute("DELETE FROM custom_patterns WHERE id=?", (pattern_id,)))
