"""Enrollment FSM: tap → 10s capture → transcribe → embed → write row."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from cue import audio, db, embed, stt
from cue.config import ENROLL_SECONDS


def run_enrollment(
    db_path: Path,
    on_status: Callable[[str], None] = lambda _m: None,
) -> db.Person | None:
    """Capture 10s, transcribe, extract name, embed, write row.

    Falls back to `Unnamed-<timestamp>` if name extraction fails.
    Returns the newly-written Person, or None on failure.
    """
    # Warm the Resemblyzer + Whisper models up front so the "Embedding..." step
    # after the user speaks is ~150ms instead of 30s on a cold Python process.
    import numpy as np

    on_status("Preparing models (first run takes ~30s)...")
    embed.embed(np.zeros(16_000, dtype=np.float32))
    stt.transcribe(np.zeros(16_000, dtype=np.float32))

    on_status(f"Listening for {ENROLL_SECONDS:.0f}s — speak now...")
    wav = audio.record_fixed(ENROLL_SECONDS)

    on_status("Transcribing...")
    text = stt.transcribe(wav)
    name = stt.extract_name(text) or f"Unnamed-{int(time.time())}"

    on_status(f"Embedding voice for {name}...")
    vec = embed.embed(wav)

    on_status(f"Saving {name}...")
    new_id = db.insert_person(
        db_path,
        name=name,
        embedding=vec,
        intro_text=text,
        source_context="temple_tap_enroll",
    )
    rows = db.all_people(db_path)
    person = next((p for p in rows if p.id == new_id), None)
    if person is not None:
        on_status(f"Enrolled #{person.id}: {person.name}")
    return person
