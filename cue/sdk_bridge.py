"""WebSocket bridge to the React plugin running inside the Even app WebView.

Protocol (JSON lines):

Python → React (commands):
  {"type": "send_card", "title": str, "lines": [str], "ttl_ms": int}
  {"type": "clear_card"}

React → Python (events):
  {"type": "temple_tap", "side": "left"|"right", "count": int}
  {"type": "head_shake"}

The React plugin subscribes to the real Even Hub SDK (onEvenHubEvent / IMU),
translates into this protocol, and calls textContainerUpgrade / container APIs
when it receives send_card / clear_card. All Even-SDK method names stay on the
React side — the Python side never imports an Even SDK.
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Callable, Literal

from cue.config import BRIDGE_HOST, BRIDGE_PORT

log = logging.getLogger(__name__)

TempleTapCallback = Callable[[Literal["left", "right"], int], None]
HeadShakeCallback = Callable[[], None]


class EvenBridge:
    """WebSocket server Python side hosts; React plugin dials in on startup.

    Running the server on Python means the plugin can reconnect freely whenever
    the Even app reopens the WebView. The laptop's IP has to be reachable from
    the phone for the real-glasses demo — for simulator testing, localhost is
    fine.
    """

    def __init__(self, host: str = BRIDGE_HOST, port: int = BRIDGE_PORT) -> None:
        self._host = host
        self._port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server = None
        self._clients: set = set()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._tap_cbs: list[TempleTapCallback] = []
        self._shake_cbs: list[HeadShakeCallback] = []

    def on_temple_tap(self, cb: TempleTapCallback) -> None:
        self._tap_cbs.append(cb)

    def on_head_shake(self, cb: HeadShakeCallback) -> None:
        self._shake_cbs.append(cb)

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="even-bridge"
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._loop and self._server:
            self._loop.call_soon_threadsafe(self._server.close)
        if self._thread:
            self._thread.join(timeout=2.0)

    def send_card(self, title: str, lines: list[str], ttl_ms: int) -> None:
        self._broadcast(
            {"type": "send_card", "title": title, "lines": lines, "ttl_ms": ttl_ms}
        )

    def clear_card(self) -> None:
        self._broadcast({"type": "clear_card"})

    # ---- internals ------------------------------------------------------

    def _run_loop(self) -> None:
        try:
            import websockets  # imported here to keep module-load cheap
        except ImportError:
            log.error("websockets not installed; bridge is a no-op")
            return

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def handler(ws):
            self._clients.add(ws)
            log.info("bridge client connected (%d total)", len(self._clients))
            try:
                async for raw in ws:
                    self._on_message(raw)
            except Exception:
                log.exception("bridge client error")
            finally:
                self._clients.discard(ws)
                log.info("bridge client disconnected (%d total)", len(self._clients))

        async def _main():
            self._server = await websockets.serve(handler, self._host, self._port)
            log.info("EvenBridge listening on ws://%s:%s", self._host, self._port)
            await self._server.wait_closed()

        try:
            self._loop.run_until_complete(_main())
        except Exception:
            log.exception("bridge loop crashed")
        finally:
            self._loop.close()

    def _on_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("bad json from bridge: %r", raw[:120])
            return
        kind = msg.get("type")
        if kind == "temple_tap":
            side = msg.get("side", "right")
            count = int(msg.get("count", 1))
            for cb in self._tap_cbs:
                try:
                    cb(side, count)
                except Exception:
                    log.exception("temple_tap cb failed")
        elif kind == "head_shake":
            for cb in self._shake_cbs:
                try:
                    cb()
                except Exception:
                    log.exception("head_shake cb failed")
        else:
            log.debug("ignoring bridge msg: %s", kind)

    def _broadcast(self, payload: dict) -> None:
        n_clients = len(self._clients)
        if not self._loop:
            log.warning("broadcast dropped: event loop not ready: %s", payload.get("type"))
            return
        if n_clients == 0:
            log.warning(
                "broadcast dropped: NO clients connected: %s",
                payload.get("type"),
            )
            return
        log.info("broadcast %s -> %d client(s)", payload.get("type"), n_clients)
        data = json.dumps(payload)

        async def _send_all():
            dead = []
            for c in list(self._clients):
                try:
                    await c.send(data)
                except Exception:
                    dead.append(c)
            for c in dead:
                self._clients.discard(c)

        asyncio.run_coroutine_threadsafe(_send_all(), self._loop)
