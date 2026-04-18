"""Seed the DB with 4 pitch personas.

Scenario: Even Realities Builders' Day. The wearer (you) spent the morning
meeting people. Each row below captures what was said at enrollment, plus
notes from later conversations. Voiceprints are *synthetic* — distinct
random vectors so the 4 rows are distinguishable in the DB, but they won't
match any real speaker on stage.

For the live demo, enroll each real teammate with `cue enroll` AFTER running
this script. That overwrites the synthetic voiceprint with the real one while
keeping all the rich context (brief + notes + intro).

Usage:
  .venv/bin/python scripts/seed_pitch_data.py          # seed (preserves existing)
  .venv/bin/python scripts/seed_pitch_data.py --reset  # wipe + reseed
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np

from cue import db
from cue.config import DB_PATH

# ---------------------------------------------------------------------------
# The personas
# ---------------------------------------------------------------------------

PITCH_PERSONAS = [
    {
        "name": "Javeed Sanganakal",
        "voice_seed": 101,
        "intro_text": (
            "Hey, I'm Javeed. I'm building Cue on the Even G2. "
            "Product engineer, ex-Acme. LinkedIn: linkedin.com/in/javeedsk."
        ),
        "brief": {
            "headline": "Product eng building Cue",
            "context": "Pitches at 4pm, G2 project",
            "followup": "Ask how the pitch went",
        },
        "user_note": (
            "[2026-04-18 10:20] Met at coffee bar. Showed early Cue build. "
            "He offered to co-present at G2 community demo night."
        ),
        "match_count": 7,
        "minutes_ago": 25,
    },
    {
        "name": "Abhishek Jaiswal",
        "voice_seed": 202,
        "intro_text": (
            "I'm Abhishek, co-building Cue with Javeed. I come from infra, "
            "was at Acme on the platform team. Happy to trade notes on "
            "ambient wearables. linkedin.com/in/abhishekj720."
        ),
        "brief": {
            "headline": "Infra eng, Cue co-builder",
            "context": "Owns bridge + plugin plumbing",
            "followup": "Ask about G2 BLE quirks",
        },
        "user_note": (
            "[2026-04-18 09:45] Walked through the WS bridge design. "
            "Agreed to pair on the demo-seed script tonight."
        ),
        "match_count": 12,
        "minutes_ago": 8,
    },
    {
        "name": "Tim Chen",
        "voice_seed": 303,
        "intro_text": (
            "Tim Chen, staff engineer at Anthropic working on the Claude API. "
            "Came by to see what folks are building with wearables. "
            "Hit me up: linkedin.com/in/timchen-anthropic."
        ),
        "brief": {
            "headline": "Staff eng @ Anthropic, API",
            "context": "Met at Claude booth, 10am",
            "followup": "Ask about prompt caching tips",
        },
        "user_note": (
            "[2026-04-18 10:05] Gave him a quick Cue demo at the API booth. "
            "Offered a mentor call; said to email 'tchen@anthropic.com' next week. "
            "He wanted to see the adaptive-thinking pattern in summarize.py."
        ),
        "match_count": 3,
        "minutes_ago": 55,
    },
    {
        "name": "Priya Subramanian",
        "voice_seed": 404,
        "intro_text": (
            "Hi, I'm Priya. Product designer at Acme Corp, leading the Q3 "
            "onboarding flow. I'm exploring AR UX patterns and really liked "
            "how minimal the G2 HUD is. linkedin.com/in/priya-subr."
        ),
        "brief": {
            "headline": "PM design @ Acme, Q3 lead",
            "context": "Owes you beta invite link",
            "followup": "Ask about onboarding friction",
        },
        "user_note": (
            "[2026-04-18 11:30] She walked us through the Acme onboarding "
            "wireframes. Promised to send the beta invite by Friday. "
            "Strong opinion against modal dialogs in AR."
        ),
        "match_count": 5,
        "minutes_ago": 40,
    },
]


def _synth_voice(seed: int) -> np.ndarray:
    """Deterministic, L2-normalized 256-d vector — distinct per seed."""
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(256).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return vec


def _insert_persona(persona: dict) -> int:
    """Insert one persona and populate all the extra fields."""
    embedding = _synth_voice(persona["voice_seed"])
    person_id = db.insert_person(
        DB_PATH,
        name=persona["name"],
        embedding=embedding,
        intro_text=persona["intro_text"],
        source_context="pitch_seed",
    )
    db.set_brief(DB_PATH, person_id, json.dumps(persona["brief"]))
    db.append_note(DB_PATH, person_id, persona["user_note"])

    # Backfill the timestamps + match_count so `cue list` reads as believable.
    import sqlite3

    now = int(time.time())
    last_seen = now - persona["minutes_ago"] * 60
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE people SET last_seen_at = ?, match_count = ? WHERE id = ?",
        (last_seen, persona["match_count"], person_id),
    )
    conn.commit()
    conn.close()
    return person_id


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset", action="store_true", help="delete all existing rows first"
    )
    args = parser.parse_args(argv)

    db.init_db(DB_PATH)

    if args.reset:
        existing = db.all_people(DB_PATH)
        for p in existing:
            db.delete_person(DB_PATH, p.id)
        print(f"deleted {len(existing)} existing rows")

    for persona in PITCH_PERSONAS:
        pid = _insert_persona(persona)
        print(f"  #{pid:<3} {persona['name']}")
    print(f"seeded {len(PITCH_PERSONAS)} personas")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
