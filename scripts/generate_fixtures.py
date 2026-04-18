"""Record a few fixture wavs under tests/fixtures/ for use in tests and demo seeding.

Run: `.venv/bin/python scripts/generate_fixtures.py <name1> [<name2> ...]`

Each argument becomes `tests/fixtures/<name>.wav`. Captures 4 seconds per name.
"""
from __future__ import annotations

import sys
from pathlib import Path

import soundfile as sf

from cue import audio
from cue.config import SAMPLE_RATE

OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: generate_fixtures.py <name1> [<name2> ...]", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for name in argv:
        input(f"Press Enter, then speak for 4s as '{name}'...")
        wav = audio.record_fixed(4.0)
        out = OUT / f"{name}.wav"
        sf.write(str(out), wav, SAMPLE_RATE, subtype="PCM_16")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
