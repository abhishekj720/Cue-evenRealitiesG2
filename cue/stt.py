"""faster-whisper wrapper: wav → text. Plus best-effort name extraction."""
from __future__ import annotations

import re
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=1)
def _model():
    from faster_whisper import WhisperModel

    # tiny.en for speed; switch to base.en in config if accuracy is poor.
    return WhisperModel("tiny.en", device="cpu", compute_type="int8")


def transcribe(wav: np.ndarray, sr: int = 16_000) -> str:
    """Return the best-effort transcript (stripped)."""
    if sr != 16_000:
        raise ValueError(f"transcribe() expects 16kHz, got {sr}")
    model = _model()
    audio = wav.astype(np.float32)
    segments, _info = model.transcribe(audio, language="en", vad_filter=False)
    return " ".join(s.text for s in segments).strip()


_NAME_PATTERNS = [
    # "I'm Priya" / "I am Priya Subramanian"
    re.compile(r"\bI(?:'m| am)\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)?)\b"),
    # "my name is Priya"
    re.compile(r"\bmy name is\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)?)\b", re.I),
    # "this is Priya"
    re.compile(r"\bthis is\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)?)\b", re.I),
]


def extract_name(text: str) -> str | None:
    """Best-effort name extraction. Regex only — never call an LLM here."""
    if not text:
        return None
    for pat in _NAME_PATTERNS:
        m = pat.search(text)
        if m:
            return m.group(1).strip()
    return None
