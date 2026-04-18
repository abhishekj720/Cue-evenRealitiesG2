"""Format a Person into a HUD card and push it via the bridge."""
from __future__ import annotations

import time

from cue.config import CARD_TTL_MS
from cue.db import Person

LINE_MAX = 28


def render_card(bridge, person: Person, score: float | None = None) -> None:
    """Truncate to `LINE_MAX` per line and push via the bridge."""
    title = person.name[:LINE_MAX]
    lines: list[str] = []

    if person.blurb:
        lines.append(person.blurb[:LINE_MAX])
    elif person.intro_text:
        lines.append(person.intro_text[:LINE_MAX])

    lines.append(_last_seen_line(person.last_seen_at))

    if person.user_note:
        # Show only the latest note line.
        latest = person.user_note.splitlines()[-1][:LINE_MAX]
        lines.append(latest)

    bridge.send_card(title=title, lines=lines, ttl_ms=CARD_TTL_MS)


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
