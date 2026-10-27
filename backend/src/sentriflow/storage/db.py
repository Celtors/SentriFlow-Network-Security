import sqlite3
from pathlib import Path

from sentriflow.core.models import Flow, Verdict


class Database:
    """All runtime access occurs on the shared API/proxy loop; no payload is accepted here."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(Path(__file__).with_name("schema.sql").read_text())
        self.connection.commit()
        versions = [row[0] for row in self.connection.execute("SELECT version FROM schema_version")]
        if versions != [1]:
            raise RuntimeError("Unsupported database schema; do not overwrite existing data")
        for (data,) in self.connection.execute("SELECT data FROM flows").fetchall():
            flow = Flow.model_validate_json(data)
            if flow.state == "held":
                flow.state, flow.verdict, flow.verdict_source = (
                    "completed",
                    Verdict.BLOCK,
                    "recovery",
                )
                flow.deadline, flow.reason = None, "Previous session ended before decision"
                with self.connection:
                    self.connection.execute(
                        "UPDATE flows SET verdict=?, data=? WHERE id=?",
                        (flow.verdict.value, flow.model_dump_json(), flow.id),
                    )

    def close(self) -> None:
        self.connection.close()
