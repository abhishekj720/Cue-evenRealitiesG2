"""Cosine match against an in-memory list of Person rows.

Linear scan is fine for < 500 rows. If we hit that, swap in hnswlib.
"""
from __future__ import annotations

import numpy as np

from cue.db import Person


def best_match(
    query: np.ndarray,
    people: list[Person],
    threshold: float = 0.75,
) -> tuple[Person, float] | None:
    """Return (person, score) if the top-1 cosine similarity ≥ threshold, else None.

    Both `query` and `person.embedding` are assumed L2-normalized — so cosine is a
    plain dot product. We recompute the norms anyway to be defensive.
    """
    if not people:
        return None
    q = _normalize(query)
    mat = np.stack([_normalize(p.embedding) for p in people])
    scores = mat @ q
    idx = int(np.argmax(scores))
    top = float(scores[idx])
    if top < threshold:
        return None
    return people[idx], top


def _normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v
