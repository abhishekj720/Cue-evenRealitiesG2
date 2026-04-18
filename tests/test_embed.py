"""embed() output is the right shape and L2-normalized."""
from __future__ import annotations

import numpy as np
import pytest

from cue import embed
from cue.config import SAMPLE_RATE


@pytest.mark.slow
def test_embed_shape_and_norm():
    # Use a deterministic pseudo-signal; Resemblyzer works on any audio shape.
    rng = np.random.default_rng(42)
    wav = rng.standard_normal(SAMPLE_RATE * 2).astype(np.float32) * 0.1
    vec = embed.embed(wav, sr=SAMPLE_RATE)
    assert vec.shape == (256,)
    assert vec.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(vec), 1.0, atol=1e-4)
