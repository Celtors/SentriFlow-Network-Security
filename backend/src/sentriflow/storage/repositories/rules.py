from sentriflow.core.models import Rule
from sentriflow.storage.db import Database


class RuleRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def list(self) -> list[Rule]:
        return [
            Rule(**r) for r in await self.db.fetch("SELECT * FROM rules ORDER BY created_at DESC")
        ]

    async def save(self, rule: Rule) -> Rule:
        data = rule.model_dump(mode="json")
        await self.db.execute(
            "INSERT INTO rules VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
            "process_match=excluded.process_match, host_match=excluded.host_match, "
            "action=excluded.action, note=excluded.note",
            tuple(data.values()),
        )
        return rule

    async def delete(self, rule_id: str) -> bool:
        return bool(await self.db.execute("DELETE FROM rules WHERE id=?", (rule_id,)))
