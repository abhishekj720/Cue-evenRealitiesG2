"""Claude-generated HUD content.

Two outputs:
- `six_word_blurb(intro)` — original 6-word one-liner.
- `generate_brief(intro, note)` — structured 3-line brief with a follow-up
  prompt, meant to be rendered directly on the HUD when a match fires.

Both are best-effort: return None when unavailable so callers never block.
"""
from __future__ import annotations

import json
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
        for block in msg.content:
            if block.type == "text":
                out = block.text.strip().strip(".")
                return out or None
    except Exception:
        log.exception("blurb generation failed")
    return None


_BRIEF_SYSTEM = """You render tiny HUD cards for a pair of smart glasses.

The wearer just heard a known person speak. You help the wearer remember
them and pick the best next thing to say.

Given the intro transcript (what the person said when the wearer first
enrolled them) and any notes the wearer attached, output a STRICT JSON
object with exactly these keys:

{
  "headline": "<up to 28 chars: role + company/context>",
  "context":  "<up to 28 chars: last promise, fact, or known tension>",
  "followup": "<up to 28 chars: one line the wearer could say or ask next>"
}

Constraints:
- ASCII only. No emojis, no curly quotes, no markdown.
- Each value MUST be <= 28 characters.
- Prefer verbs in the followup, imperative voice ("ask about...", "remind that...").
- Never invent facts. If the intro is thin, keep it abstract ("new contact", "recent meet").

Return ONLY the JSON. No prose, no code fences."""


def _offline_brief(intro_text: str, name: str | None = None) -> dict:
    """Rule-based fallback brief when Claude is unavailable.

    Not clever — just reframes the intro into three ≤28-char lines so the
    HUD card renders something useful.
    """
    text = (intro_text or "").strip()
    # Chop intro_text into speech-like beats.
    parts = [p.strip() for p in text.replace("\n", ".").split(".") if p.strip()]
    headline = parts[0] if parts else (name or "known contact")
    context = parts[1] if len(parts) > 1 else "no notes yet"
    followup = "ask what they're working on"
    return {
        "headline": headline[:28],
        "context": context[:28],
        "followup": followup[:28],
    }


def generate_brief(
    intro_text: str,
    user_note: str | None = None,
    offline_fallback: bool = True,
) -> dict | None:
    """Return {headline, context, followup}. Tries Claude; falls back offline.

    Returns None only if both paths fail (no intro_text at all).
    """
    if not intro_text:
        return None

    if ANTHROPIC_API_KEY:
        try:
            import anthropic

            payload = f"Intro: {intro_text}"
            if user_note:
                payload += f"\nWearer's notes:\n{user_note}"
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            msg = client.messages.create(
                model=BLURB_MODEL,
                max_tokens=200,
                system=_BRIEF_SYSTEM,
                messages=[{"role": "user", "content": payload}],
            )
            raw = "".join(
                b.text for b in msg.content if getattr(b, "type", "") == "text"
            ).strip()
            data = json.loads(raw)
            out = {
                "headline": str(data.get("headline", ""))[:28],
                "context": str(data.get("context", ""))[:28],
                "followup": str(data.get("followup", ""))[:28],
            }
            if any(out.values()):
                return out
        except ImportError:
            log.info("anthropic not installed; using offline brief")
        except Exception as exc:
            log.warning("claude brief failed (%s); using offline brief", exc)

    if offline_fallback:
        return _offline_brief(intro_text)
    return None


def enqueue_blurb(db_path: Path, person_id: int, intro_text: str) -> None:
    """Fire-and-forget: compute blurb + brief on a background thread."""
    def _work() -> None:
        blurb = six_word_blurb(intro_text)
        if blurb:
            db.set_blurb(db_path, person_id, blurb)
            log.info("blurb set for #%s: %r", person_id, blurb)
        brief = generate_brief(intro_text)
        if brief:
            db.set_brief(db_path, person_id, json.dumps(brief))
            log.info("brief set for #%s: %s", person_id, brief)

    threading.Thread(target=_work, daemon=True, name="summarize").start()
