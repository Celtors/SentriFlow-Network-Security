import json
from typing import Any

from sentriflow.core.models import Flow
from sentriflow.storage.db import Database


class AlertsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db.connection

    def record(self, flow: Flow) -> list[dict[str, Any]]:
        alerts = [
            {
                "id": f"{flow.id}:{i}",
                "flow_id": flow.id,
                "ts": flow.ts,
                "type": f.type,
                "severity": "high" if f.type == "pii" else "medium",
                "pattern_label": f.label,
                "masked_sample": f.masked_sample,
                "host": flow.host,
                "process_name": flow.process_name,
            }
            for i, f in enumerate(flow.findings)
        ]
        with self.db:
            for alert in alerts:
                self.db.execute(
                    "INSERT OR REPLACE INTO alerts VALUES (?, ?, ?, ?)",
                    (alert["id"], flow.id, flow.ts, json.dumps(alert)),
                )
        return alerts

    def list(self, limit: int = 200) -> list[dict[str, Any]]:
        return [
            json.loads(row[0])
            for row in self.db.execute("SELECT data FROM alerts ORDER BY ts DESC LIMIT ?", (limit,))
        ]
