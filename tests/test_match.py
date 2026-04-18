"""Match.best_match picks the right person above threshold, None below."""
from __future__ import annotations

import numpy as np

from cue import db, match


def _dummy_person(pid: int, vec: np.ndarray) -> db.Person:
    return db.Person(
        id=pid,
        name=f"p{pid}",
        embedding=vec,
        intro_text=None,
        blurb=None,
        brief=None,
        user_note=None,
        source_context=None,
        created_at=0,
        last_seen_at=0,
        match_count=0,
    )


def test_match_picks_closest_above_threshold():
    rng = np.random.default_rng(7)
    a = rng.standard_normal(256).astype(np.float32)
    a /= np.linalg.norm(a)
    b = rng.standard_normal(256).astype(np.float32)
    b /= np.linalg.norm(b)

    people = [_dummy_person(1, a), _dummy_person(2, b)]

    # Query very close to `a` — a small perturbation.
    perturb = rng.standard_normal(256).astype(np.float32) * 0.05
    q = (a + perturb)
    q /= np.linalg.norm(q)

    result = match.best_match(q, people, threshold=0.75)
    assert result is not None
    person, score = result
    assert person.id == 1
    assert score > 0.75


def test_match_returns_none_below_threshold():
    rng = np.random.default_rng(11)
    vecs = [rng.standard_normal(256).astype(np.float32) for _ in range(3)]
    vecs = [v / np.linalg.norm(v) for v in vecs]
    people = [_dummy_person(i + 1, v) for i, v in enumerate(vecs)]

    # A totally unrelated vector — orthogonal on expectation.
    q = rng.standard_normal(256).astype(np.float32)
    q /= np.linalg.norm(q)

    result = match.best_match(q, people, threshold=0.95)  # impossibly strict
    assert result is None
