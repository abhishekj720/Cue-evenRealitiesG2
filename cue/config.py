"""Paths, thresholds, and constants. Read once, referenced everywhere."""
from __future__ import annotations

import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """Tiny .env loader — sets os.environ for any KEY=VALUE lines in the file.

    Existing env vars win. Comments and blank lines are skipped.
    """
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Load ./.env relative to the project root so every cue entrypoint sees
# ANTHROPIC_API_KEY without requiring the user to `export` it manually.
_load_env_file(Path(__file__).resolve().parent.parent / ".env")

# Local data dir — all persistent state lives here.
DATA_DIR: Path = Path(os.environ.get("CUE_DATA_DIR", Path.home() / ".cue")).expanduser()
DB_PATH: Path = DATA_DIR / "people.db"

# Audio pipeline.
SAMPLE_RATE: int = 16_000
CHANNELS: int = 1
VAD_BLOCK_MS: int = 20
ENROLL_SECONDS: float = 10.0
NOTE_SECONDS: float = 5.0

# Matching.
MATCH_THRESHOLD: float = 0.65
DEDUP_WINDOW_S: int = 60
CARD_TTL_MS: int = 6_000

# Recognition loop.
ROLLING_SEGMENT_S: float = 3.0

# WebSocket bridge to the React plugin in the Even app.
# 0.0.0.0 so the plugin running on a phone (real G2 demo) can reach this
# laptop over the LAN. 127.0.0.1 is fine for the simulator-only flow.
BRIDGE_HOST: str = os.environ.get("CUE_BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT: int = int(os.environ.get("CUE_BRIDGE_PORT", "8765"))

# Optional Claude blurb.
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")
# Haiku is the right model for a 6-word summarization task (fast, cheap, sufficient).
BLURB_MODEL: str = "claude-haiku-4-5"


def ensure_data_dir() -> None:
    """Create the local data dir if missing."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
