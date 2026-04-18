"""Resemblyzer wrapper: wav → 256-d L2-normalized float32 vector."""
from __future__ import annotations

from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _encoder():
    # Lazy import keeps module load cheap for tests that don't need the model.
    from resemblyzer import VoiceEncoder

    return VoiceEncoder()


def embed(wav: np.ndarray, sr: int = 16_000) -> np.ndarray:
    """Return a 256-d L2-normalized float32 vector for the given waveform.

    wav: mono float32 waveform in [-1, 1].
    """
    enc = _encoder()
    # Resemblyzer expects float32 in [-1, 1] at 16kHz. Handle int16 input.
    if wav.dtype != np.float32:
        wav = wav.astype(np.float32)
        if wav.max() > 1.5 or wav.min() < -1.5:
            wav = wav / 32768.0
    if sr != 16_000:
        raise ValueError(f"embed() expects 16kHz, got {sr}")
    vec = enc.embed_utterance(wav)
    vec = np.asarray(vec, dtype=np.float32)
    norm = float(np.linalg.norm(vec))
    if norm > 0:
        vec = vec / norm
    return vec
