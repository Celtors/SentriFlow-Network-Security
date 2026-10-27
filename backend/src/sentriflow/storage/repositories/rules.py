from sentriflow.core.models import Rule
from sentriflow.storage.db import Database


class RulesRepository:
    def __init__(self, db: Database) -> None:
        self.db = db.connection

    def list(self) -> list[Rule]:
        return [
            Rule.model_validate_json(r[0])
            for r in self.db.execute("SELECT data FROM rules ORDER BY rowid DESC")
        ]

    def save(self, rule: Rule) -> Rule:
        with self.db:
            self.db.execute(
                """INSERT INTO rules VALUES (?, ?, ?, ?)
                ON CONFLICT(process_match, host_match) DO UPDATE SET
                id=excluded.id, data=excluded.data""",
                (rule.id, rule.process_match, rule.host_match, rule.model_dump_json()),
            )
        return rule

    def delete(self, rule_id: str) -> bool:
        with self.db:
            return self.db.execute("DELETE FROM rules WHERE id=?", (rule_id,)).rowcount > 0
