"""End-to-end pipeline test without a microphone.

Proves: embed → DB → match → RecognitionLoop → EvenBridge → WebSocket → client
receives a send_card message. If this passes, the only thing that can go wrong
in `cue run` is the live-mic → VAD path.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np
import websockets

from cue import db, embed, recognize, sdk_bridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("e2e")


def make_person_audio(seed: int, seconds: float = 3.0) -> np.ndarray:
    """A synthetic speech-like signal Resemblyzer is happy to embed."""
    rng = np.random.default_rng(seed)
    sr = 16_000
    n = int(seconds * sr)
    # Mix a slowly-modulating tone with noise — enough variation that
    # Resemblyzer's VAD doesn't discard it as silence.
    t = np.arange(n) / sr
    f0 = 150.0
    tone = 0.25 * np.sin(2 * np.pi * f0 * t + 2 * np.sin(2 * np.pi * 2 * t))
    noise = 0.05 * rng.standard_normal(n)
    return (tone + noise).astype(np.float32)


def main() -> int:
    # 1. Fresh DB, enroll a synthetic person.
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "people.db"
        db.init_db(db_path)
        wav = make_person_audio(seed=7)
        vec = embed.embed(wav)
        pid = db.insert_person(
            db_path, name="TestPerson", embedding=vec, intro_text="end-to-end test"
        )
        log.info("enrolled #%s TestPerson", pid)

        # 2. Start the bridge.
        bridge = sdk_bridge.EvenBridge(host="127.0.0.1", port=8766)  # non-default port
        bridge.start()
        time.sleep(0.5)

        # 3. Spin up a plugin-like WS client that collects messages.
        received: list[dict] = []
        client_ready = threading.Event()
        client_done = threading.Event()

        def run_client():
            async def _client():
                async with websockets.connect("ws://127.0.0.1:8766") as ws:
                    client_ready.set()
                    # Collect messages for up to 4 seconds.
                    async def collect():
                        async for raw in ws:
                            received.append(json.loads(raw))
                    try:
                        await asyncio.wait_for(collect(), timeout=4.0)
                    except asyncio.TimeoutError:
                        pass
                    client_done.set()

            asyncio.run(_client())

        t = threading.Thread(target=run_client, daemon=True)
        t.start()
        client_ready.wait(timeout=2.0)
        time.sleep(0.2)
        log.info("plugin-simulator WS client connected")

        # 4. Feed one "speech segment" (the same wav) into recognition.
        def segments():
            yield wav

        loop = recognize.RecognitionLoop(db_path, bridge, segments(), threshold=0.5)
        start = time.time()
        loop.start()

        # 5. Wait for the card.
        client_done.wait(timeout=5.0)
        elapsed = time.time() - start
        loop.stop()
        bridge.stop()
        t.join(timeout=2.0)

        log.info("recognition → WS elapsed: %.3fs", elapsed)
        log.info("messages received: %d", len(received))
        for msg in received:
            log.info("  %s", msg)

        ok = any(m.get("type") == "send_card" for m in received)
        print("---")
        print("RESULT:", "PASS ✅" if ok else "FAIL ❌")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
