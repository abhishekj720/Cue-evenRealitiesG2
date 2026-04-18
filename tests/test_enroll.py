"""Enrollment round-trips an embedding through the DB.

True speaker-discrimination verification requires real wav fixtures — run
`scripts/generate_fixtures.py <name>` to record 4s clips and drop them under
`tests/fixtures/`. The slow test below embeds non-speech noise only to verify
the pipeline (embed → DB → match) connects correctly.
"""
from __future__ import annotations

import numpy as np
import pytest

from cue import db, match
from cue.config import SAMPLE_RATE


@pytest.mark.slow
def test_pipeline_round_trip(tmp_path):
    """Embed → insert → re-embed same audio → best_match returns the row."""
    from cue import embed

    rng = np.random.default_rng(42)
    wav = (rng.standard_normal(SAMPLE_RATE * 3) * 0.1).astype(np.float32)

    db_path = tmp_path / "people.db"
    db.init_db(db_path)
    v = embed.embed(wav)
    pid = db.insert_person(db_path, name="Alice", embedding=v, intro_text=None)
    assert pid > 0

    # Same audio → top-1 match with very high cosine.
    q = embed.embed(wav)
    people = db.all_people(db_path)
    result = match.best_match(q, people, threshold=0.9)
    assert result is not None
    person, score = result
    assert person.name == "Alice"
    assert score > 0.99
