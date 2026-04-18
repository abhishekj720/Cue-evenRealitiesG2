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
        """Consume raw mic frames; feed silero-vad in fixed 512-sample chunks.

        sounddevice delivers 20ms frames (=320 samples at 16kHz), but silero-vad
        requires exactly 512 samples per call. We accumulate a rolling byte
        buffer and slice it into 512-sample VAD chunks.
        """
        from silero_vad import load_silero_vad, VADIterator

        model = load_silero_vad()
        vad = VADIterator(model, sampling_rate=SAMPLE_RATE)
        CHUNK = 512

        pending = np.empty(0, dtype=np.float32)  # leftover samples between frames
        seg_buf: list[np.ndarray] = []
        voiced_len = 0
        in_speech = False

        # Mic heartbeat — log peak RMS every ~1s so the user can verify audio
        # is actually flowing in even when VAD doesn't fire.
        hb_samples = 0
        hb_peak_rms = 0.0
        hb_every = SAMPLE_RATE  # 1 second

        while not self._stop.is_set():
            try:
                frame = self._q.get(timeout=0.2)
            except queue.Empty:
                continue
            hb_samples += len(frame)
            rms = float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))
            hb_peak_rms = max(hb_peak_rms, rms)
            if hb_samples >= hb_every:
                log.info("mic heartbeat: peak_rms=%.4f (last %.1fs)", hb_peak_rms, hb_samples / SAMPLE_RATE)
                hb_samples = 0
                hb_peak_rms = 0.0
            pending = (
                np.concatenate([pending, frame]) if pending.size else frame
            )
            # Consume as many 512-sample chunks as available.
            while len(pending) >= CHUNK:
                chunk = pending[:CHUNK]
                pending = pending[CHUNK:]
                result = vad(chunk, return_seconds=False)
                if in_speech:
                    seg_buf.append(chunk)
                    voiced_len += CHUNK
                if result is not None:
                    if "start" in result and not in_speech:
                        in_speech = True
                        seg_buf = [chunk]
                        voiced_len = CHUNK
                    if "end" in result and in_speech:
                        if voiced_len >= self._min_len:
                            seg = np.concatenate(seg_buf)[: self._max_len]
                            log.info(
                                "vad: emitting speech segment (%.2fs)",
                                len(seg) / SAMPLE_RATE,
                            )
                            try:
                                self._segments.put_nowait(seg)
                            except queue.Full:
                                pass
                        seg_buf = []
                        voiced_len = 0
                        in_speech = False
