"""Claude-backed text translation for the live-caption mode.

Usage:
    from cue.translate import translate_text
    translated = translate_text("Hello", target="Spanish")
"""
from __future__ import annotations

import logging

from cue.config import ANTHROPIC_API_KEY, BLURB_MODEL

log = logging.getLogger(__name__)


def translate_text(text: str, target: str, source: str = "auto") -> str | None:
    """Return translation of `text` into `target`, or None on failure."""
    text = (text or "").strip()
    if not text or not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
    except ImportError:
        log.warning("anthropic not installed; translation disabled")
        return None

    src_hint = "" if source == "auto" else f" The source language is {source}."
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=BLURB_MODEL,
            max_tokens=300,
            system=(
                "You are a precise real-time translator. Output ONLY the target-"
                "language translation. Never add commentary, quotation marks, "
                "language names, or markdown. Preserve punctuation and tone."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Translate into {target}.{src_hint}\n\n"
                        f"TEXT:\n{text}"
                    ),
                }
            ],
        )
        raw = "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        ).strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1].strip()
        return raw.strip("\"'")
    except Exception as exc:
        log.warning("translation failed: %s", exc)
        return None
