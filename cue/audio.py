"""Microphone capture + VAD segmentation.

- `MicStream`: context manager, 16kHz mono, 20ms blocks, iter_segments() yields
  VAD-gated speech segments (≥ 1s padded) as float32 np.ndarrays.
- `record_fixed(seconds)`: synchronous N-second capture. Used by enrollment + note.
"""
from __future__ import annotations

import logging
import queue
import threading
from contextlib import AbstractContextManager
from typing import Iterator

import numpy as np

from cue.config import CHANNELS, SAMPLE_RATE, VAD_BLOCK_MS

log = logging.getLogger(__name__)


def record_fixed(seconds: float) -> np.ndarray:
    """Synchronously capture exactly `seconds` of mono 16kHz audio."""
    import sounddevice as sd

    frames = int(seconds * SAMPLE_RATE)
    buf = sd.rec(frames, samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
    sd.wait()
    return buf.reshape(-1).astype(np.float32)


class MicStream(AbstractContextManager["MicStream"]):
    """Live microphone stream with VAD-based speech segmentation."""

    def __init__(self, min_segment_s: float = 1.0, max_segment_s: float = 6.0) -> None:
        self._min_len = int(min_segment_s * SAMPLE_RATE)
        self._max_len = int(max_segment_s * SAMPLE_RATE)
        self._q: queue.Queue[np.ndarray] = queue.Queue(maxsize=256)
        self._stream = None
        self._segments: queue.Queue[np.ndarray] = queue.Queue(maxsize=64)
        self._vad_thread: threading.Thread | None = None
        self._stop = threading.Event()

    def __enter__(self) -> "MicStream":
        import sounddevice as sd

        block = int(SAMPLE_RATE * VAD_BLOCK_MS / 1000)

        def cb(indata, _frames, _time, _status):  # sounddevice callback
            self._q.put_nowait(indata.copy().reshape(-1).astype(np.float32))

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=block,
            callback=cb,
        )
        self._stream.start()
        self._vad_thread = threading.Thread(target=self._vad_loop, daemon=True)
        self._vad_thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        self._stop.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        if self._vad_thread is not None:
            self._vad_thread.join(timeout=1.0)

    def iter_segments(self) -> Iterator[np.ndarray]:
        """Yield VAD-gated speech segments as float32 arrays at 16kHz."""
        while not self._stop.is_set():
            try:
                seg = self._segments.get(timeout=0.2)
            except queue.Empty:
                continue
            yield seg

    def _vad_loop(self) -> None:
        """Consume raw 20ms frames; group voiced frames into segments."""
        from silero_vad import load_silero_vad, VADIterator

        model = load_silero_vad()
        vad = VADIterator(model, sampling_rate=SAMPLE_RATE)
        buf: list[np.ndarray] = []
        voiced_len = 0

        while not self._stop.is_set():
            try:
                frame = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            # silero-vad needs 512-sample chunks at 16kHz (32ms). Slice accordingly.
            for chunk in _chunks(frame, 512):
                result = vad(chunk, return_seconds=False)
                buf.append(chunk)
                voiced_len += len(chunk)
                if result is not None and "end" in result:
                    if voiced_len >= self._min_len:
                        seg = np.concatenate(buf)[: self._max_len]
                        log.info(
                            "vad: emitting speech segment (%.2fs)",
                            len(seg) / SAMPLE_RATE,
                        )
                        try:
                            self._segments.put_nowait(seg)
                        except queue.Full:
                            pass
                    buf.clear()
                    voiced_len = 0


def _chunks(arr: np.ndarray, size: int):
    for i in range(0, len(arr) - size + 1, size):
        yield arr[i : i + size]
