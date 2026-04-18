"""Double-tap → 5s audio window → append transcript to last-matched person.user_note."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable

from cue import audio, db, stt
from cue.config import NOTE_SECONDS

log = logging.getLogger(__name__)

# A double-tap more than 30 seconds after the card is ignored — by then the
# context is stale and the user probably meant something else.
NOTE_WINDOW_AFTER_MATCH_S = 30


def run_note(
    db_path: Path,
    person_id: int,
    on_status: Callable[[str], None] = lambda _m: None,
) -> bool:
    """Capture NOTE_SECONDS of audio, transcribe, append to user_note. Return True on write."""
    on_status(f"Listening {NOTE_SECONDS:.0f}s for note...")
    wav = audio.record_fixed(NOTE_SECONDS)

    on_status("Transcribing note...")
    text = stt.transcribe(wav)
    if not text:
        on_status("Empty note — discarded.")
        return False

    stamped = f"[{time.strftime('%Y-%m-%d %H:%M')}] {text}"
    db.append_note(db_path, person_id, stamped)
    on_status(f"Note saved on person #{person_id}.")
    return True
