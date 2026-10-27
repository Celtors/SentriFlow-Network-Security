from sentriflow.core.models import Flow, utcnow
from sentriflow.storage.db import Database


class FlowsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db.connection

    def save(self, flow: Flow) -> None:
        flow.updated_at = utcnow()
        with self.db:
            self.db.execute(
                """INSERT INTO flows VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET verdict=excluded.verdict, data=excluded.data""",
                (
                    flow.id,
                    flow.ts,
                    flow.process_key,
                    flow.process_name,
                    flow.host,
                    flow.verdict.value,
                    flow.model_dump_json(),
                ),
            )
            self.db.execute("""DELETE FROM flows WHERE id IN (
                SELECT id FROM flows WHERE json_extract(data, '$.state') IN ('completed','error')
                ORDER BY ts DESC LIMIT -1 OFFSET 10000)""")

    def get(self, flow_id: str) -> Flow | None:
        row = self.db.execute("SELECT data FROM flows WHERE id=?", (flow_id,)).fetchone()
        return Flow.model_validate_json(row[0]) if row else None

    def list(
        self, limit: int = 200, process: str | None = None, verdict: str | None = None
    ) -> list[Flow]:
        return [
            Flow.model_validate_json(row[0])
            for row in self.db.execute(
                """SELECT data FROM flows WHERE (? IS NULL OR process_name=?)
               AND (? IS NULL OR verdict=?) ORDER BY ts DESC LIMIT ?""",
                (process, process, verdict, verdict, limit),
            )
        ]
