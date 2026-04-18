"""Recognition loop: rolling segments → embed → match → push HUD card."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Iterable, Protocol

import numpy as np

from cue import db, embed, hud, match, stt
from cue.config import (
    CARD_TTL_MS,
    DEDUP_SILENCE_RESET_S,
    DEDUP_WINDOW_S,
    MATCH_THRESHOLD,
)

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
        echo: bool = False,
    ) -> None:
        self._db_path = db_path
        self._bridge = bridge
        self._segments = segments
        self._threshold = threshold
        self._echo = echo
        self._last_shown: dict[int, float] = {}      # when card last pushed
        self._last_matched_at: dict[int, float] = {}  # when speech last matched
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
            if self._echo:
                self._push_echo_card(seg, top_person.name, top_score)
            return
        person, score = top_person, top_score
        now = time.time()
        last = self._last_shown.get(person.id, 0.0)
        last_matched = self._last_matched_at.get(person.id, 0.0)
        silence_since_last_match = now - last_matched if last_matched else None
        # If the person went silent for DEDUP_SILENCE_RESET_S, treat this as a
        # new encounter and re-surface the card — picks up the conversation.
        reset_by_silence = (
            silence_since_last_match is not None
            and silence_since_last_match > DEDUP_SILENCE_RESET_S
        )
        self._last_matched_at[person.id] = now
        if now - last < DEDUP_WINDOW_S and not reset_by_silence:
            log.info("skip dedup: %s score=%.3f", person.name, score)
            return
        self._last_shown[person.id] = now
        self._last_matched_id = person.id
        db.update_last_seen(self._db_path, person.id, int(now))
        log.info("MATCH %s score=%.3f -> push card", person.name, score)
        hud.render_card(self._bridge, person, score=score)

    def _push_echo_card(self, seg: np.ndarray, top_name: str, top_score: float) -> None:
        """Debug helper: transcribe the segment and show it on the HUD."""
        try:
            text = stt.transcribe(seg)
        except Exception:
            log.exception("echo transcribe failed")
            return
        snippet = (text or "(silence)")[:56]
        log.info("echo: heard %r (top=%s %.2f)", snippet, top_name, top_score)
        self._bridge.send_card(
            title="heard",
            lines=[snippet[:28], snippet[28:56], f"best={top_name} {top_score:.2f}"],
            ttl_ms=CARD_TTL_MS,
        )
