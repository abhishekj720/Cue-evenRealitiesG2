"""Recognition loop: rolling segments → embed → match → push HUD card."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Iterable, Protocol

import numpy as np

from cue import db, embed, hud, match
from cue.config import DEDUP_WINDOW_S, MATCH_THRESHOLD

log = logging.getLogger(__name__)


class Bridge(Protocol):
    def send_card(self, title: str, lines: list[str], ttl_ms: int) -> None: ...
    def clear_card(self) -> None: ...


class RecognitionLoop:
    """Consumes speech segments, matches against DB, pushes HUD cards.

    Respects a per-person dedup window so we don't spam the HUD.
    """

    def __init__(
        self,
        db_path: Path,
        bridge: Bridge,
        segments: Iterable[np.ndarray],
        threshold: float = MATCH_THRESHOLD,
    ) -> None:
        self._db_path = db_path
        self._bridge = bridge
        self._segments = segments
        self._threshold = threshold
        self._last_shown: dict[int, float] = {}
        self._last_matched_id: int | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def last_matched_id(self) -> int | None:
        return self._last_matched_id

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="recognize")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run(self) -> None:
        try:
            for seg in self._segments:
                if self._stop.is_set():
                    break
                self._handle_segment(seg)
        except Exception:  # top-of-thread guard per project style
            log.exception("recognition loop crashed")

    def _handle_segment(self, seg: np.ndarray) -> None:
        people = db.all_people(self._db_path)
        if not people:
            log.info("segment received but DB empty — run `cue enroll` first")
            return
        vec = embed.embed(seg)
        # Log the top score even below threshold so the user can tune.
        top = match.best_match(vec, people, threshold=0.0)
        if top is None:
            return
        top_person, top_score = top
        if top_score < self._threshold:
            log.info(
                "no match: top=%s score=%.3f (threshold %.2f)",
                top_person.name,
                top_score,
                self._threshold,
            )
            return
        person, score = top_person, top_score
        now = time.time()
        last = self._last_shown.get(person.id, 0.0)
        if now - last < DEDUP_WINDOW_S:
            log.info("skip dedup: %s score=%.3f", person.name, score)
            return
        self._last_shown[person.id] = now
        self._last_matched_id = person.id
        db.update_last_seen(self._db_path, person.id, int(now))
        log.info("MATCH %s score=%.3f -> push card", person.name, score)
        hud.render_card(self._bridge, person, score=score)
