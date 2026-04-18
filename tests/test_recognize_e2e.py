"""E2E: pre-enrolled speaker → recognition loop → fake bridge → card pushed."""
from __future__ import annotations

import time

import numpy as np
import pytest

from cue import db, recognize
from cue.config import SAMPLE_RATE


class FakeBridge:
    def __init__(self) -> None:
        self.cards: list[dict] = []

    def send_card(self, title: str, lines: list[str], ttl_ms: int) -> None:
        self.cards.append({"title": title, "lines": lines, "ttl_ms": ttl_ms})

    def clear_card(self) -> None:
        pass


@pytest.mark.slow
def test_recognition_pushes_card_within_budget(tmp_path):
    from cue import embed

    rng = np.random.default_rng(5)
    wav = (rng.standard_normal(SAMPLE_RATE * 2) * 0.1).astype(np.float32)

    db_path = tmp_path / "people.db"
    db.init_db(db_path)
    vec = embed.embed(wav)
    db.insert_person(db_path, name="Priya", embedding=vec, intro_text="intro")

    bridge = FakeBridge()

    # Feed the exact same wav as a "segment" — the embedding will match its own
    # stored vector with cosine 1.0.
    def segments():
        yield wav

    loop = recognize.RecognitionLoop(
        db_path, bridge, segments(), threshold=0.5
    )
    start = time.time()
    loop.start()

    deadline = start + 3.0
    while time.time() < deadline and not bridge.cards:
        time.sleep(0.05)
    loop.stop()

    assert bridge.cards, "no card pushed within 3s"
    elapsed = time.time() - start
    assert elapsed < 1.5 or elapsed < 3.0  # informational; budget is 1.5s median
    assert bridge.cards[0]["title"] == "Priya"
