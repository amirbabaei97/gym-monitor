"""SQLite storage: one row per gym visit, keyed by its check-in time."""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
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


# user_version 1: app check-ins are stored with correct times (see fix_app_times).
SCHEMA_VERSION = 1


@contextmanager
def connect(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        fresh = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'sessions'").fetchone() is None
        conn.executescript(SCHEMA)
        if fresh:
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
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


def fix_app_times(conn: sqlite3.Connection, zone) -> int:
    """One-time fix for databases written before user_version 1.

    Back then Netpulse's naive check-in times were taken as local time, but they
    are UTC. Each 'app' row's wall-clock time is re-read as UTC and stored in
    `zone`. Returns the number of rows fixed (0 once done).
    """
    if conn.execute("PRAGMA user_version").fetchone()[0] >= 1:
        return 0

    def fix(value: str | None) -> str | None:
        if not value:
            return value
        naive = datetime.fromisoformat(value).replace(tzinfo=None)
        return naive.replace(tzinfo=timezone.utc).astimezone(zone).isoformat(timespec="seconds")

    rows = conn.execute("SELECT * FROM sessions WHERE source = 'app'").fetchall()
    conn.execute("DELETE FROM sessions WHERE source = 'app'")
    conn.executemany(
        "INSERT OR IGNORE INTO sessions (checkin, checkout, studio, source, updated) VALUES (?, ?, ?, ?, ?)",
        [(fix(r["checkin"]), fix(r["checkout"]), r["studio"], r["source"], r["updated"]) for r in rows],
    )
    conn.execute("PRAGMA user_version = 1")
    return len(rows)


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
