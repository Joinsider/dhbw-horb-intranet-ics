import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

from .parser import Event

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    kurs TEXT NOT NULL,
    week_start TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL,
    title TEXT NOT NULL,
    person TEXT NOT NULL,
    room TEXT NOT NULL,
    kind TEXT NOT NULL,
    color TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_kurs_week ON events (kurs, week_start);
CREATE TABLE IF NOT EXISTS weeks (
    kurs TEXT NOT NULL,
    week_start TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    PRIMARY KEY (kurs, week_start)
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=30)

    def replace_week(
        self, kurs: str, week_start: date, events: list[Event], fetched_at: float
    ) -> None:
        week = week_start.isoformat()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "DELETE FROM events WHERE kurs = ? AND week_start = ?", (kurs, week)
            )
            conn.executemany(
                "INSERT INTO events (kurs, week_start, start, end, title, person, room, kind, color)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (kurs, week, e.start.isoformat(), e.end.isoformat(),
                     e.title, e.person, e.room, e.kind, e.color)
                    for e in events
                ],
            )
            conn.execute(
                "INSERT INTO weeks (kurs, week_start, fetched_at) VALUES (?, ?, ?)"
                " ON CONFLICT (kurs, week_start) DO UPDATE SET fetched_at = excluded.fetched_at",
                (kurs, week, fetched_at),
            )

    def fetched_at(self, kurs: str) -> dict[date, float]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT week_start, fetched_at FROM weeks WHERE kurs = ?", (kurs,)
            ).fetchall()
        return {date.fromisoformat(week): ts for week, ts in rows}

    def events(self, kurs: str, before: date) -> list[Event]:
        """All stored events of a course that start before the given day."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT start, end, title, person, room, kind, color FROM events"
                " WHERE kurs = ? AND start < ? ORDER BY start, title, room",
                (kurs, before.isoformat()),
            ).fetchall()
        return [
            Event(datetime.fromisoformat(s), datetime.fromisoformat(e), *rest)
            for s, e, *rest in rows
        ]

    def get_meta(self, key: str) -> str | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                "INSERT INTO meta (key, value) VALUES (?, ?)"
                " ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
