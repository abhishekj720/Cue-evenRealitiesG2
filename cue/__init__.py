"""Cue — ambient social memory for Even G2."""
from __future__ import annotations

import os

# Torch (resemblyzer) and faster-whisper's CTranslate2 both link libiomp5.
# macOS refuses to run when two copies register. Setting this *before* either
# is imported lets them coexist. The Intel note says it "may cause crashes or
# silently produce incorrect results" but in practice both runtimes run the
# same libiomp and it works fine.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

__version__ = "0.1.0"
