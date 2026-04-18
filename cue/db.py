"""SQLite schema + CRUD for the `people` table.

Embeddings are stored as raw bytes (`np.asarray(vec, dtype=np.float32).tobytes()`)
and read back with `np.frombuffer(..., dtype=np.float32)`. No ORM — stdlib sqlite3
with parameterized queries.
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    embedding     BLOB NOT NULL,
    intro_text    TEXT,
    blurb         TEXT,
    brief         TEXT,
    user_note     TEXT,
    source_context TEXT,
    created_at    INTEGER NOT NULL,
    last_seen_at  INTEGER NOT NULL,
    match_count   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_last_seen ON people(last_seen_at);
"""


# Lightweight online migration so existing DBs pick up the new `brief` column.
_MIGRATIONS = [
    "ALTER TABLE people ADD COLUMN brief TEXT",
]


def _apply_migrations(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(people)")}
    if "brief" not in existing:
        conn.execute("ALTER TABLE people ADD COLUMN brief TEXT")


@dataclass
class Person:
    id: int
    name: str
    embedding: np.ndarray
    intro_text: str | None
    blurb: str | None
    brief: str | None
    user_note: str | None
    source_context: str | None
    created_at: int
    last_seen_at: int
    match_count: int


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path) -> None:
    """Create schema if missing, then apply any pending column migrations."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(path) as conn:
        conn.executescript(SCHEMA)
        _apply_migrations(conn)


def insert_person(
    path: Path,
    name: str,
    embedding: np.ndarray,
    intro_text: str | None,
    source_context: str | None = None,
) -> int:
    """Insert a new row, return the new id."""
    now = int(time.time())
    blob = np.asarray(embedding, dtype=np.float32).tobytes()
    with _connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO people (name, embedding, intro_text, source_context, "
            "created_at, last_seen_at, match_count) "
            "VALUES (?, ?, ?, ?, ?, ?, 0)",
            (name, blob, intro_text, source_context, now, now),
        )
        return int(cur.lastrowid)


def update_last_seen(path: Path, person_id: int, ts: int) -> None:
    with _connect(path) as conn:
        conn.execute(
            "UPDATE people SET last_seen_at = ?, match_count = match_count + 1 "
            "WHERE id = ?",
            (ts, person_id),
        )


def append_note(path: Path, person_id: int, note: str) -> None:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT user_note FROM people WHERE id = ?", (person_id,)
        ).fetchone()
        if row is None:
            return
        existing = row["user_note"] or ""
        joined = f"{existing}\n{note}".strip() if existing else note
        conn.execute(
            "UPDATE people SET user_note = ? WHERE id = ?", (joined, person_id)
        )


def set_blurb(path: Path, person_id: int, blurb: str) -> None:
    with _connect(path) as conn:
        conn.execute(
            "UPDATE people SET blurb = ? WHERE id = ?", (blurb, person_id)
        )


def all_people(path: Path) -> list[Person]:
    with _connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM people ORDER BY last_seen_at DESC"
        ).fetchall()
    return [_row_to_person(r) for r in rows]


def delete_person(path: Path, person_id: int) -> None:
    with _connect(path) as conn:
        conn.execute("DELETE FROM people WHERE id = ?", (person_id,))


def set_brief(path: Path, person_id: int, brief: str) -> None:
    with _connect(path) as conn:
        conn.execute(
            "UPDATE people SET brief = ? WHERE id = ?", (brief, person_id)
        )


def set_embedding(path: Path, person_id: int, embedding: np.ndarray) -> None:
    """Replace a person's voiceprint while keeping their name/intro/notes."""
    blob = np.asarray(embedding, dtype=np.float32).tobytes()
    with _connect(path) as conn:
        conn.execute(
            "UPDATE people SET embedding = ? WHERE id = ?", (blob, person_id)
        )


def _row_to_person(row: sqlite3.Row) -> Person:
    keys = row.keys()
    return Person(
        id=row["id"],
        name=row["name"],
        embedding=np.frombuffer(row["embedding"], dtype=np.float32),
        intro_text=row["intro_text"],
        blurb=row["blurb"],
        brief=row["brief"] if "brief" in keys else None,
        user_note=row["user_note"],
        source_context=row["source_context"],
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
        match_count=row["match_count"],
    )
