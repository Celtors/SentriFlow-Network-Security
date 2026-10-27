import asyncio
from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None
        self.lock = asyncio.Lock()

    async def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        try:
            self.connection.row_factory = aiosqlite.Row
            await self.connection.execute("PRAGMA journal_mode=WAL")
            await self.connection.execute("PRAGMA foreign_keys=ON")
            version = (await self.fetch("PRAGMA user_version"))[0]["user_version"]
            if version > 2:
                raise ValueError("Database was created by a newer SentriFlow version")
            columns = await self.fetch("PRAGMA table_info(flows)")
            if columns and "findings_json" not in {row["name"] for row in columns}:
                raise ValueError(
                    "Database uses a different prototype schema; "
                    "preserve it and use a new --data-dir"
                )
            for number, filename in ((1, "001_init.sql"), (2, "002_dashboard.sql")):
                if number <= version:
                    continue
                migration = Path(__file__).with_name("migrations") / filename
                await self.connection.executescript(
                    "BEGIN IMMEDIATE;\n"
                    + migration.read_text()
                    + f"\nPRAGMA user_version={number};\nCOMMIT;"
                )
        except BaseException:
            await self.close()
            raise

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()
            self.connection = None

    async def fetch(self, sql: str, values: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        assert self.connection is not None
        async with self.lock, self.connection.execute(sql, values) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def execute(self, sql: str, values: tuple[Any, ...] = ()) -> int:
        assert self.connection is not None
        async with self.lock:
            try:
                async with self.connection.execute(sql, values) as cursor:
                    affected = cursor.rowcount
                await self.connection.commit()
                return affected
            except BaseException:
                await self.connection.rollback()
                raise
