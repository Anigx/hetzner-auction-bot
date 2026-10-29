"""SQLite-Speicher für Kanalbindung, Filter, Baseline, Posts und Warteschlange."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Sequence

from filters import Criteria, FilterRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS guilds (
    guild_id    INTEGER PRIMARY KEY,
    channel_id  INTEGER NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS filters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    name          TEXT NOT NULL,
    criteria_json TEXT NOT NULL,
    mention       INTEGER NOT NULL DEFAULT 0,
    active        INTEGER NOT NULL DEFAULT 1,
    baseline_pending INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (guild_id, user_id, name)
);

CREATE TABLE IF NOT EXISTS seen (
    filter_id INTEGER NOT NULL,
    server_id INTEGER NOT NULL,
    PRIMARY KEY (filter_id, server_id)
);

CREATE TABLE IF NOT EXISTS posts (
    guild_id       INTEGER NOT NULL,
    server_id      INTEGER NOT NULL,
    last_price_eur TEXT NOT NULL,
    posted_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (guild_id, server_id)
);

CREATE TABLE IF NOT EXISTS baselines (
    guild_id    INTEGER NOT NULL,
    server_id   INTEGER NOT NULL,
    price_eur   TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (guild_id, server_id)
);

CREATE TABLE IF NOT EXISTS queue (
    guild_id     INTEGER NOT NULL,
    server_id    INTEGER NOT NULL,
    filter_ids   TEXT NOT NULL,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    attempts     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, server_id)
);
"""


@dataclass(frozen=True)
class QueuedItem:
    guild_id: int
    server_id: int
    filter_ids: tuple[int, ...]
    attempts: int


class Store:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(self.path))
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA foreign_keys=ON")

    def init_schema(self) -> None:
        self._db.executescript(SCHEMA)
        # Migration fuer Datenbanken aus der Zeit vor baseline_pending.
        try:
            self._db.execute(
                "ALTER TABLE filters ADD COLUMN baseline_pending INTEGER NOT NULL DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    # -- Kanalbindung -----------------------------------------------------

    def set_channel(self, guild_id: int, channel_id: int) -> None:
        self._db.execute(
            """
            INSERT INTO guilds (guild_id, channel_id, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(guild_id) DO UPDATE SET
                channel_id = excluded.channel_id,
                updated_at = excluded.updated_at
            """,
            (guild_id, channel_id),
        )
        self._db.commit()

    def get_channel(self, guild_id: int) -> int | None:
        row = self._db.execute(
            "SELECT channel_id FROM guilds WHERE guild_id = ?", (guild_id,)
        ).fetchone()
        return None if row is None else int(row["channel_id"])

    # -- Filter -----------------------------------------------------------

    @staticmethod
    def _to_record(row: sqlite3.Row) -> FilterRecord:
        return FilterRecord(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]),
            name=str(row["name"]),
            criteria=Criteria.from_json(json.loads(row["criteria_json"])),
            mention=bool(row["mention"]),
            active=bool(row["active"]),
            baseline_pending=bool(row["baseline_pending"]),
        )

    def save_filter(
        self,
        guild_id: int,
        user_id: int,
        name: str,
        criteria: Criteria,
        mention: bool,
    ) -> FilterRecord:
        self._db.execute(
            """
            INSERT INTO filters (guild_id, user_id, name, criteria_json, mention, active)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(guild_id, user_id, name) DO UPDATE SET
                criteria_json = excluded.criteria_json,
                mention = excluded.mention,
                active = 1
            """,
            (guild_id, user_id, name, json.dumps(criteria.to_json()), int(mention)),
        )
        self._db.commit()
        record = self.get_filter(guild_id, user_id, name)
        assert record is not None
        return record

    def get_filter(self, guild_id: int, user_id: int, name: str) -> FilterRecord | None:
        row = self._db.execute(
            "SELECT * FROM filters WHERE guild_id = ? AND user_id = ? AND name = ?",
            (guild_id, user_id, name),
        ).fetchone()
        return None if row is None else self._to_record(row)

    def list_filters(
        self,
        guild_id: int | None = None,
        user_id: int | None = None,
        active_only: bool = False,
    ) -> list[FilterRecord]:
        clauses: list[str] = []
        params: list[object] = []
        if guild_id is not None:
            clauses.append("guild_id = ?")
            params.append(guild_id)
        if user_id is not None:
            clauses.append("user_id = ?")
            params.append(user_id)
        if active_only:
            clauses.append("active = 1")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._db.execute(
            f"SELECT * FROM filters{where} ORDER BY guild_id, user_id, name", params
        ).fetchall()
        return [self._to_record(row) for row in rows]

    def delete_filter(self, guild_id: int, user_id: int, name: str) -> bool:
        record = self.get_filter(guild_id, user_id, name)
        if record is None:
            return False
        self._db.execute("DELETE FROM seen WHERE filter_id = ?", (record.id,))
        self._db.execute("DELETE FROM filters WHERE id = ?", (record.id,))
        self._db.commit()
        return True

    def set_active(self, guild_id: int, user_id: int, name: str, active: bool) -> bool:
        cursor = self._db.execute(
            "UPDATE filters SET active = ? WHERE guild_id = ? AND user_id = ? AND name = ?",
            (int(active), guild_id, user_id, name),
        )
        self._db.commit()
        return cursor.rowcount > 0

    def set_baseline_pending(self, filter_id: int, pending: bool) -> None:
        self._db.execute(
            "UPDATE filters SET baseline_pending = ? WHERE id = ?", (int(pending), filter_id)
        )
        self._db.commit()

    # -- Baseline ---------------------------------------------------------

    def mark_seen(self, filter_id: int, server_ids: Iterable[int]) -> None:
        self._db.executemany(
            "INSERT OR IGNORE INTO seen (filter_id, server_id) VALUES (?, ?)",
            [(filter_id, int(server_id)) for server_id in server_ids],
        )
        self._db.commit()

    def is_seen(self, filter_id: int, server_id: int) -> bool:
        row = self._db.execute(
            "SELECT 1 FROM seen WHERE filter_id = ? AND server_id = ?",
            (filter_id, server_id),
        ).fetchone()
        return row is not None

    # -- Posts ------------------------------------------------------------

    def last_price(self, guild_id: int, server_id: int) -> Decimal | None:
        row = self._db.execute(
            "SELECT last_price_eur FROM posts WHERE guild_id = ? AND server_id = ?",
            (guild_id, server_id),
        ).fetchone()
        return None if row is None else Decimal(row["last_price_eur"])

    def record_post(self, guild_id: int, server_id: int, price: Decimal) -> None:
        self._db.execute(
            """
            INSERT INTO posts (guild_id, server_id, last_price_eur, posted_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(guild_id, server_id) DO UPDATE SET
                last_price_eur = excluded.last_price_eur,
                posted_at = excluded.posted_at
            """,
            (guild_id, server_id, str(price)),
        )
        self._db.commit()

    # -- Baseline ---------------------------------------------------------

    def record_baseline(self, guild_id: int, server_id: int, price: Decimal) -> None:
        self._db.execute(
            """
            INSERT INTO baselines (guild_id, server_id, price_eur, recorded_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(guild_id, server_id) DO UPDATE SET
                price_eur = excluded.price_eur,
                recorded_at = excluded.recorded_at
            """,
            (guild_id, server_id, str(price)),
        )
        self._db.commit()

    def baseline_price(self, guild_id: int, server_id: int) -> Decimal | None:
        row = self._db.execute(
            "SELECT price_eur FROM baselines WHERE guild_id = ? AND server_id = ?",
            (guild_id, server_id),
        ).fetchone()
        return None if row is None else Decimal(row["price_eur"])

    # -- Warteschlange ----------------------------------------------------

    def enqueue(self, guild_id: int, server_id: int, filter_ids: Sequence[int]) -> None:
        self._db.execute(
            """
            INSERT INTO queue (guild_id, server_id, filter_ids)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, server_id) DO NOTHING
            """,
            (guild_id, server_id, json.dumps(sorted(int(f) for f in filter_ids))),
        )
        self._db.commit()

    def queued(self) -> list[QueuedItem]:
        rows = self._db.execute(
            "SELECT * FROM queue ORDER BY first_seen_at, guild_id, server_id"
        ).fetchall()
        return [
            QueuedItem(
                guild_id=int(row["guild_id"]),
                server_id=int(row["server_id"]),
                filter_ids=tuple(json.loads(row["filter_ids"])),
                attempts=int(row["attempts"]),
            )
            for row in rows
        ]

    def dequeue(self, guild_id: int, server_id: int) -> None:
        self._db.execute(
            "DELETE FROM queue WHERE guild_id = ? AND server_id = ?", (guild_id, server_id)
        )
        self._db.commit()

    def bump_attempts(self, guild_id: int, server_id: int) -> int:
        self._db.execute(
            "UPDATE queue SET attempts = attempts + 1 WHERE guild_id = ? AND server_id = ?",
            (guild_id, server_id),
        )
        self._db.commit()
        row = self._db.execute(
            "SELECT attempts FROM queue WHERE guild_id = ? AND server_id = ?",
            (guild_id, server_id),
        ).fetchone()
        return 0 if row is None else int(row["attempts"])
