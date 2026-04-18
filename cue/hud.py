"""Format a Person into a HUD card and push it via the bridge."""
from __future__ import annotations

import json
import time

from cue.config import CARD_TTL_MS
from cue.db import Person

LINE_MAX = 28


def render_card(bridge, person: Person, score: float | None = None) -> None:
    """Truncate to `LINE_MAX` per line and push via the bridge.

    Line priority (most informative first):
      1. structured brief (AI-generated): headline / context / followup
      2. legacy blurb (6 words)
      3. raw intro_text (Whisper transcript from enrollment)
    """
    title = person.name[:LINE_MAX]
    lines: list[str] = []

    brief = _parse_brief(person.brief)
    if brief:
        for key in ("headline", "context", "followup"):
            v = brief.get(key)
            if v:
                lines.append(str(v)[:LINE_MAX])
    elif person.blurb:
        lines.append(person.blurb[:LINE_MAX])
    elif person.intro_text:
        lines.append(person.intro_text[:LINE_MAX])

    lines.append(_last_seen_line(person.last_seen_at))

    if person.user_note and not brief:
        # If there's a brief, Claude already factored notes in. Otherwise
        # show the most recent note line directly.
        latest = person.user_note.splitlines()[-1][:LINE_MAX]
        lines.append(latest)

    bridge.send_card(title=title, lines=lines, ttl_ms=CARD_TTL_MS)


def _parse_brief(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass
    return None


def _last_seen_line(ts: int) -> str:
    now = int(time.time())
    delta = max(0, now - ts)
    days = delta // 86_400
    if days == 0:
        hours = delta // 3_600
        if hours == 0:
            return "seen just now"
        return f"seen {hours}h ago"
    if days == 1:
        return "seen 1 day ago"
    return f"seen {days} days ago"
