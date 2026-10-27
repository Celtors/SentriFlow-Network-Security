from sentriflow.storage.db import Database


class BlocklistRepository:
    def __init__(self, db: Database) -> None:
        self.db = db.connection

    def domains(self) -> set[str]:
        return {
            r[0] for r in self.db.execute("SELECT domain FROM blocklist_domains WHERE enabled=1")
        }

    def add(self, domains: set[str], source: str) -> None:
        with self.db:
            self.db.executemany(
                "INSERT OR IGNORE INTO blocklist_domains VALUES (?, ?, 1)",
                ((domain, source) for domain in domains),
            )

    def status(self) -> list[dict[str, str | int]]:
        return [
            {"source": r[0], "count": r[1]}
            for r in self.db.execute(
                "SELECT source, count(*) FROM blocklist_domains GROUP BY source"
            )
        ]
