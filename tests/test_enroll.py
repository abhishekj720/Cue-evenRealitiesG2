"""Enrollment uses pre-recorded wavs via the seeding path — no live mic."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from cue import db, match
from cue.config import SAMPLE_RATE


@pytest.mark.slow
def test_same_speaker_round_trips(tmp_path):
    """Two embeddings of the same pseudo-speaker match; two different ones don't.

    This is a placeholder until real wav fixtures are committed — uses the same
    random seed twice to simulate "same speaker", and different seeds for
    "different speaker".
    """
    from cue import embed

    rng1a = np.random.default_rng(42)
    rng1b = np.random.default_rng(42)
    rng2 = np.random.default_rng(99)

    wav1a = (rng1a.standard_normal(SAMPLE_RATE * 2) * 0.1).astype(np.float32)
    wav1b = (rng1b.standard_normal(SAMPLE_RATE * 2) * 0.1).astype(np.float32)
    wav2 = (rng2.standard_normal(SAMPLE_RATE * 2) * 0.1).astype(np.float32)

    db_path = tmp_path / "people.db"
    db.init_db(db_path)
    v1 = embed.embed(wav1a)
    db.insert_person(db_path, name="Alice", embedding=v1, intro_text=None)

    v1b = embed.embed(wav1b)
    v2 = embed.embed(wav2)

    people = db.all_people(db_path)
    same_result = match.best_match(v1b, people, threshold=0.5)
    diff_result = match.best_match(v2, people, threshold=0.99)

    assert same_result is not None
    assert diff_result is None
