from __future__ import annotations

import json
from typing import Any

from sentriflow.core.models import Flow
from sentriflow.storage.db import Database


class FlowRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, flow: Flow) -> None:
        data = flow.model_dump(mode="json", exclude={"findings"})
        data["findings_json"] = json.dumps([f.model_dump() for f in flow.findings])
        columns = ",".join(data)
        placeholders = ",".join("?" for _ in data)
        updates = ",".join(f"{key}=excluded.{key}" for key in data if key != "id")
        await self.db.execute(
            f"INSERT INTO flows ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(id) DO UPDATE SET {updates}",
            tuple(data.values()),
        )

    async def list(
        self,
        *,
        process: str | None = None,
        verdict: str | None = None,
        since: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Flow]:
        clauses, values = [], []
        for column, value, operator in (
            ("process_name", process, "="),
            ("verdict", verdict, "="),
            ("ts", since, ">="),
        ):
            if value is not None:
                clauses.append(f"{column} {operator} ?")
                values.append(value)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = await self.db.fetch(
            f"SELECT * FROM flows{where} ORDER BY ts DESC LIMIT ? OFFSET ?",
            (*values, limit, offset),
        )
        result = []
        for row in rows:
            findings = json.loads(row.pop("findings_json"))
            result.append(Flow(**row, findings=findings))
        return result

    async def processes(self) -> list[dict[str, Any]]:
        return await self.db.fetch(
            "SELECT process_name, pid, COUNT(*) AS connections, SUM(bytes_up) AS bytes_up, "
            "SUM(bytes_down) AS bytes_down, COUNT(DISTINCT host) AS hosts "
            "FROM flows GROUP BY process_name, pid ORDER BY bytes_up DESC"
        )

    async def score(self) -> dict[str, Any]:
        from sentriflow.core.scoring import score

        # Aggregate in SQLite instead of loading unbounded history into memory.
        result = score([])
        for kind in ("pii", "tracker"):
            types = "('pii','custom')" if kind == "pii" else "('tracker')"
            rows = await self.db.fetch(
                "SELECT verdict, COUNT(*) AS count FROM flows WHERE verdict IN ('allow','block') "
                "AND EXISTS (SELECT 1 FROM json_each(findings_json) "
                f"WHERE json_extract(value, '$.type') IN {types}) GROUP BY verdict"
            )
            for row in rows:
                key = ("blocked" if row["verdict"] == "block" else "allowed") + "_" + kind
                result["breakdown"][key] = row["count"]
        delta = sum(result["weights"][k] * v for k, v in result["breakdown"].items())
        result["score"] = min(100, max(0, 100 + delta))
        return result
