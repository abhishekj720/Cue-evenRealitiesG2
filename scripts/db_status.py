"""Quick DB peek: who's enrolled, how many matches, last-seen.

Run: `.venv/bin/python scripts/db_status.py`
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

DB = Path.home() / ".cue" / "people.db"


def main() -> int:
    if not DB.exists():
        print("no db at", DB)
        return 1
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, match_count, last_seen_at, intro_text, user_note FROM people"
    ).fetchall()
    if not rows:
        print("(no enrolled people)")
        return 0
    now = int(time.time())
    for r in rows:
        ago = now - r["last_seen_at"]
        print(f"#{r['id']:<3} {r['name']:<20} matches={r['match_count']:<4} "
              f"last_seen={ago}s ago")
        if r["intro_text"]:
            print(f"      intro: {r['intro_text'][:80]}")
        if r["user_note"]:
            print(f"      note: {r['user_note'][:80]}")
    return 0


if __name__ == "__main__":
    main()
