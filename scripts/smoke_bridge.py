"""Start the WebSocket bridge, push a hardcoded card once a client connects.

Run: `.venv/bin/python scripts/smoke_bridge.py`

Then point the React plugin at ws://127.0.0.1:8765 and verify the card hits the
HUD. Temple taps from the plugin will log here.
"""
from __future__ import annotations

import logging
import time

from cue import sdk_bridge

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


def main() -> None:
    bridge = sdk_bridge.EvenBridge()
    bridge.on_temple_tap(lambda side, count: print(f"tap: {side} x{count}"))
    bridge.on_head_shake(lambda: print("head_shake"))
    bridge.start()

    print("Bridge up on ws://127.0.0.1:8765")
    # Wait for a client to connect, then push a demo card every 5s.
    try:
        while True:
            time.sleep(5)
            bridge.send_card(
                title="Priya Subramanian",
                lines=[
                    "leads platform at Acme",
                    "seen 21 days ago",
                    "promised beta invite",
                ],
                ttl_ms=6_000,
            )
            print("pushed demo card")
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()
