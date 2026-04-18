"""Seed the DB from a folder of pre-recorded wavs.

Each `<Name>.wav` becomes an enrolled row — no mic, no live capture. Lets us
pre-enroll 3-4 demo teammates before the pitch so the live moment on stage is
recognition (high magic-to-risk ratio), not enrollment.
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import soundfile as sf

from cue import db, embed, stt
from cue.config import SAMPLE_RATE

log = logging.getLogger(__name__)


def seed_from_folder(db_path: Path, folder: Path) -> list[int]:
    """Enroll every .wav in `folder`; filename (stem) becomes the name."""
    db.init_db(db_path)
    new_ids: list[int] = []
    for wav_path in sorted(folder.glob("*.wav")):
        name = wav_path.stem
        wav, sr = sf.read(str(wav_path), dtype="float32", always_2d=False)
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        if sr != SAMPLE_RATE:
            # Resampling is rare here; fail loud rather than silently mis-embed.
            raise ValueError(
                f"{wav_path.name} is {sr}Hz; resample to {SAMPLE_RATE}Hz before seeding"
            )
        vec = embed.embed(wav.astype(np.float32), sr=SAMPLE_RATE)
        intro = stt.transcribe(wav.astype(np.float32)) or None
        pid = db.insert_person(
            db_path,
            name=name,
            embedding=vec,
            intro_text=intro,
            source_context=f"seed:{wav_path.name}",
        )
        log.info("seeded #%s %s from %s", pid, name, wav_path.name)
        new_ids.append(pid)
    return new_ids
