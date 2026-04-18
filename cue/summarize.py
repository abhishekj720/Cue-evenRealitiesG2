"""Optional: Claude-generated 6-word blurb.

Called after each enrollment in a background thread. Never blocks the critical
path. If ANTHROPIC_API_KEY is unset or the call fails, returns None.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

from cue import db
from cue.config import ANTHROPIC_API_KEY, BLURB_MODEL

log = logging.getLogger(__name__)


def six_word_blurb(intro_text: str) -> str | None:
    """Return a 6-word summary, or None if unavailable."""
    if not ANTHROPIC_API_KEY or not intro_text:
        return None
    try:
        import anthropic
    except ImportError:
        log.info("anthropic not installed; skipping blurb")
        return None

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=BLURB_MODEL,
            max_tokens=64,
            system=(
                "You write 6-word descriptions of people. "
                "Return exactly 6 words. ASCII only, no punctuation, no emojis."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Describe this person in 6 words: {intro_text}",
                }
            ],
        )
        # Flatten content blocks; take the first text block.
        for block in msg.content:
            if block.type == "text":
                out = block.text.strip().strip(".")
                return out or None
    except Exception:
        log.exception("blurb generation failed")
    return None


def enqueue_blurb(db_path: Path, person_id: int, intro_text: str) -> None:
    """Fire-and-forget: compute blurb on a background thread, write when done."""
    def _work() -> None:
        blurb = six_word_blurb(intro_text)
        if blurb:
            db.set_blurb(db_path, person_id, blurb)
            log.info("blurb set for #%s: %r", person_id, blurb)

    threading.Thread(target=_work, daemon=True, name="blurb").start()
