"""Tiny local translator server: serves index.html + proxies /translate to Claude.

Run:
    .venv/bin/python translator/server.py

Opens on http://127.0.0.1:8080. Set ANTHROPIC_API_KEY in .env (already wired
via cue.config).
"""
from __future__ import annotations

import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Load cue.config for .env autoload + ANTHROPIC_API_KEY.
from cue.config import ANTHROPIC_API_KEY, BLURB_MODEL

HERE = Path(__file__).resolve().parent
INDEX = HERE / "index.html"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("translator")


def translate_via_claude(text: str, target: str, source: str = "auto") -> str:
    """Return a translation of `text` into `target` using Claude Haiku."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set — add it to .env")
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    src_hint = "" if source == "auto" else f" (source language: {source})"
    prompt = (
        f"Translate the following text into {target}{src_hint}. "
        "Return ONLY the translation — no quotes, no preface, no notes, "
        "no markdown, no explanation. Preserve punctuation and tone.\n\n"
        f"TEXT:\n{text}"
    )
    msg = client.messages.create(
        model=BLURB_MODEL,
        max_tokens=400,
        system=(
            "You are a precise real-time translator. Output only the target-language "
            "translation. Never add commentary, language names, or quotation marks."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    # Defensive strip of wrapping quotes or code fences.
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1].strip()
        if raw.startswith(target.lower()):
            raw = raw[len(target):].strip()
    raw = raw.strip("\"'")
    return raw


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quieter default logging; use log.info for real events.
        log.info("%s - %s", self.client_address[0], format % args)

    def do_GET(self):  # noqa: N802
        if self.path in ("/", "/index.html"):
            body = INDEX.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self):  # noqa: N802
        if self.path != "/translate":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self.send_error(400, "bad json")
            return

        text = (payload.get("text") or "").strip()
        target = (payload.get("target") or "English").strip()
        source = (payload.get("source") or "auto").strip()

        if not text:
            self._json({"translation": ""})
            return

        try:
            translation = translate_via_claude(text, target, source)
            log.info("translated (%s → %s): %r → %r", source, target, text[:60], translation[:60])
            self._json({"translation": translation})
        except Exception as exc:  # pragma: no cover — surface to browser
            log.exception("translate failed")
            self._json({"error": str(exc)}, status=500)

    def _json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    port = 8080
    httpd = HTTPServer(("0.0.0.0", port), Handler)
    print(f"  Translator: http://localhost:{port}/")
    print(f"  LAN:        http://<your-ip>:{port}/")
    print("  Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        httpd.shutdown()


if __name__ == "__main__":
    sys.exit(main())
