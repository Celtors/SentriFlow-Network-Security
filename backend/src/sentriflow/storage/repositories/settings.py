from sentriflow.core.models import Settings
from sentriflow.storage.db import Database


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db.connection

    def get(self) -> Settings:
        row = self.db.execute("SELECT value FROM settings WHERE key='inspection'").fetchone()
        return Settings.model_validate_json(row[0]) if row else Settings()

    def save(self, settings: Settings) -> None:
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO settings VALUES ('inspection', ?)",
                (settings.model_dump_json(),),
            )
