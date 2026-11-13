"""SQLite storage: one row per gym visit, keyed by its check-in time."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    checkin   TEXT PRIMARY KEY,   -- ISO 8601 with UTC offset
    checkout  TEXT,               -- NULL while still in the gym (or never checked out)
    studio    TEXT,
    source    TEXT NOT NULL,      -- 'app' | 'csv' | 'demo'
    updated   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Visit:
    checkin: datetime
    checkout: datetime | None
    studio: str | None


@contextmanager
def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_visits(conn: sqlite3.Connection, visits: list[Visit], source: str) -> int:
    """Insert new visits, fill in check-outs that arrived later. Returns rows changed."""
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    before = conn.total_changes
    conn.executemany(
        """
        INSERT INTO sessions (checkin, checkout, studio, source, updated)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(checkin) DO UPDATE SET
            checkout = COALESCE(excluded.checkout, sessions.checkout),
            studio   = COALESCE(excluded.studio, sessions.studio),
            updated  = excluded.updated
        WHERE excluded.checkout IS NOT sessions.checkout
           OR excluded.studio IS NOT sessions.studio
        """,
        [
            (
                v.checkin.isoformat(timespec="seconds"),
                v.checkout.isoformat(timespec="seconds") if v.checkout else None,
                v.studio,
                source,
                now,
            )
            for v in visits
        ],
    )
    return conn.total_changes - before


def all_visits(conn: sqlite3.Connection) -> list[Visit]:
    rows = conn.execute("SELECT checkin, checkout, studio FROM sessions ORDER BY checkin").fetchall()
    return [
        Visit(
            datetime.fromisoformat(r["checkin"]),
            datetime.fromisoformat(r["checkout"]) if r["checkout"] else None,
            r["studio"],
        )
        for r in rows
    ]


def get_meta(conn: sqlite3.Connection, key: str) -> dict | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else None


def set_meta(conn: sqlite3.Connection, key: str, value: dict) -> None:
    conn.execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value)),
    )
