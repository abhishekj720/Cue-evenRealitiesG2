"""Capture 10s from the mic, transcribe, and print the result.

Run: `.venv/bin/python scripts/smoke_audio.py`

Use this to verify microphone + VAD + Whisper all work before running `cue enroll`.
"""
from __future__ import annotations

import logging

from cue import audio, stt

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    print("Speak for 10 seconds...")
    wav = audio.record_fixed(10.0)
    print(f"Captured {len(wav) / 16_000:.1f}s of audio.")

    text = stt.transcribe(wav)
    print(f"Transcript: {text!r}")

    name = stt.extract_name(text)
    print(f"Name extracted: {name!r}")


if __name__ == "__main__":
    main()
