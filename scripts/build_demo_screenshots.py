"""Generate HUD mockup PNGs + an end-to-end flow diagram under docs/screenshots/.

Renders at the real G2 resolution (576x288), then upscales 2x for the deck.
Uses Menlo (macOS monospace) to mimic the LVGL fixed-width look.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 576, 288
PAD = 16
BG = (0, 0, 0)
FG = (0, 232, 62)   # G2 green
DIM = (0, 150, 40)
WARN = (255, 165, 0)

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"
FONT_REG = ImageFont.truetype(FONT_PATH, 22)
FONT_BIG = ImageFont.truetype(FONT_PATH, 28)
FONT_SM = ImageFont.truetype(FONT_PATH, 16)

DIVIDER = "-" * 28


def hud(lines: list[str], *, title: str | None = None) -> Image.Image:
    """Render a HUD canvas with optional title + body lines."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # 1px inner border, same as the React plugin renders (borderWidth=1).
    d.rectangle((0, 0, W - 1, H - 1), outline=FG, width=1)
    y = PAD
    if title:
        d.text((PAD, y), title, fill=FG, font=FONT_BIG)
        y += 36
    for line in lines:
        d.text((PAD, y), line, fill=FG, font=FONT_REG)
        y += 28
    return img


def _save(img: Image.Image, name: str) -> Path:
    native = OUT / f"{name}.png"
    img.save(native)
    # 2x upscale for slide embedding. Nearest-neighbour to preserve the crisp
    # pixel look of the G2.
    big = img.resize((W * 2, H * 2), Image.Resampling.NEAREST)
    big.save(OUT / f"{name}@2x.png")
    return native


def build_hud_states() -> list[Path]:
    paths: list[Path] = []

    paths.append(_save(
        hud(["", DIVIDER, "", "Listening..."], title="Cue"),
        "01_idle",
    ))

    paths.append(_save(
        hud(["", DIVIDER, "", "Summarizing inbox..."], title="Cue"),
        "02_enrolling",
    ))

    paths.append(_save(
        hud([DIVIDER,
             "Infra eng, Cue co-builder",
             "Pairing on demo-seed script",
             "Ask how the script pairing w",
             "",
             "seen just now"], title="Abhishek Jaiswal"),
        "03_match_abhishek",
    ))

    paths.append(_save(
        hud([DIVIDER,
             "Staff eng @ Anthropic, API",
             "Mentor call pending",
             "Email him summarize.py code",
             "",
             "seen 55 min ago"], title="Tim Chen"),
        "04_match_tim",
    ))

    paths.append(_save(
        hud([DIVIDER,
             "PM design @ Acme, Q3 lead",
             "Owes you beta invite link",
             "Ask about onboarding friction",
             "",
             "seen 40 min ago"], title="Priya Subramanian"),
        "05_match_priya",
    ))

    paths.append(_save(
        hud(["", DIVIDER, "", "No urgent items.", "Tap to wake."], title="Focus mode"),
        "06_focus",
    ))

    return paths


# ---------------------------------------------------------------------------
# End-to-end flow diagram (single PNG, 1600x700)
# ---------------------------------------------------------------------------

def build_flow_diagram() -> Path:
    FW, FH = 1600, 700
    img = Image.new("RGB", (FW, FH), (250, 250, 250))
    d = ImageDraw.Draw(img)
    INK = (14, 14, 14)
    ACCENT = (0, 184, 111)
    MUTED = (107, 114, 128)

    title_font = ImageFont.truetype(FONT_PATH, 36)
    step_title = ImageFont.truetype(FONT_PATH, 18)
    step_body = ImageFont.truetype(FONT_PATH, 14)
    caption = ImageFont.truetype(FONT_PATH, 16)

    d.text((40, 40), "End-to-end flow", fill=INK, font=title_font)
    d.text((40, 90), "Speech → voiceprint → match → HUD card. ~1.5s median.",
           fill=MUTED, font=caption)

    # 5 boxes, arrow between each.
    steps = [
        ("1. Mic",
         ["Phone 4-mic array",
          "16kHz PCM stream",
          "silero-vad gates",
          "speech segments"]),
        ("2. Voiceprint",
         ["Resemblyzer",
          "wav → 256-d vector",
          "L2 normalized",
          "runs on laptop"]),
        ("3. Match",
         ["Cosine similarity",
          "vs SQLite people.db",
          "threshold 0.65",
          "60s dedup/person"]),
        ("4. Brief",
         ["Claude Haiku 4.5",
          "intro + notes",
          "→ 3-line JSON",
          "headline/ctx/followup"]),
        ("5. HUD",
         ["WebSocket send_card",
          "React plugin",
          "textContainerUpgrade",
          "6s auto-dismiss"]),
    ]
    n = len(steps)
    margin = 40
    box_w = 260
    box_h = 220
    gap = (FW - 2 * margin - n * box_w) // (n - 1)
    y0 = 180

    for i, (title, body) in enumerate(steps):
        x = margin + i * (box_w + gap)
        d.rounded_rectangle((x, y0, x + box_w, y0 + box_h), radius=14,
                            fill=(255, 255, 255), outline=ACCENT, width=2)
        d.text((x + 18, y0 + 16), title, fill=INK, font=step_title)
        for j, line in enumerate(body):
            d.text((x + 18, y0 + 60 + j * 28), line, fill=INK, font=step_body)
        if i < n - 1:
            # Arrow
            ax = x + box_w + 10
            ay = y0 + box_h // 2
            d.line((ax, ay, ax + gap - 20, ay), fill=ACCENT, width=4)
            d.polygon(
                [(ax + gap - 20, ay),
                 (ax + gap - 30, ay - 8),
                 (ax + gap - 30, ay + 8)],
                fill=ACCENT,
            )

    d.text((40, 460),
           "Privacy invariants",
           fill=INK, font=title_font)
    invariants = [
        "  •  Explicit enrollment only — no voiceprint is stored without a deliberate temple tap.",
        "  •  Local-first — ~/.cue/people.db lives on the laptop. No cloud sync.",
        "  •  Cameraless by physics — G2 has no lens. No face database exists.",
        "  •  Network only for the optional Claude brief. Match path is fully offline.",
    ]
    inv_font = ImageFont.truetype(FONT_PATH, 18)
    for i, line in enumerate(invariants):
        d.text((40, 510 + i * 32), line, fill=INK, font=inv_font)

    out = OUT / "flow_diagram.png"
    img.save(out)
    return out


# ---------------------------------------------------------------------------
# Terminal A log screenshot — shows what Javeed sees while demo is running
# ---------------------------------------------------------------------------

def build_terminal_screenshot() -> Path:
    W2, H2 = 1200, 600
    img = Image.new("RGB", (W2, H2), (18, 18, 22))
    d = ImageDraw.Draw(img)
    term_font = ImageFont.truetype(FONT_PATH, 14)
    log_lines = [
        "$ .venv/bin/python -m cue.app run --echo",
        "15:42:01  INFO cue.sdk_bridge: EvenBridge listening on ws://0.0.0.0:8765",
        "15:42:01  INFO cue.run:        cue running; Ctrl+C to exit",
        "15:42:08  INFO cue.sdk_bridge: bridge client connected (1 total)",
        "",
        "15:42:19  INFO cue.audio:     mic heartbeat: peak_rms=0.0443 (last 1.0s)",
        "15:42:21  INFO cue.audio:     vad: emitting speech segment (3.92s)",
        "15:42:22  INFO cue.recognize: MATCH Abhishek Jaiswal score=0.812 -> push card",
        "15:42:22  INFO cue.sdk_bridge: broadcast send_card -> 1 client(s)",
        "",
        "15:42:34  INFO cue.audio:     vad: emitting speech segment (2.41s)",
        "15:42:34  INFO cue.recognize: skip dedup: Abhishek Jaiswal score=0.791",
        "",
        "15:43:05  INFO cue.run:        temple double-tap: note",
        "15:43:05  INFO cue.note:       Listening 5s for note...",
        "15:43:11  INFO cue.note:       Note saved on person #15.",
        "",
        "15:43:28  INFO cue.audio:     vad: emitting speech segment (1.88s)",
        "15:43:28  INFO cue.recognize: MATCH Tim Chen score=0.724 -> push card",
        "15:43:28  INFO cue.sdk_bridge: broadcast send_card -> 1 client(s)",
    ]
    colors = [(200, 200, 200)] * len(log_lines)
    # Highlight MATCH lines green.
    for i, line in enumerate(log_lines):
        if "MATCH " in line:
            colors[i] = (80, 220, 120)
        elif "broadcast send_card" in line:
            colors[i] = (120, 200, 250)
        elif "temple" in line or "note:" in line:
            colors[i] = (255, 190, 110)
        elif line.startswith("$"):
            colors[i] = (255, 255, 255)
    for i, line in enumerate(log_lines):
        d.text((20, 20 + i * 26), line, fill=colors[i], font=term_font)
    out = OUT / "07_terminal_log.png"
    img.save(out)
    return out


def main() -> None:
    hud_paths = build_hud_states()
    flow = build_flow_diagram()
    term = build_terminal_screenshot()

    print("HUD states:")
    for p in hud_paths:
        print(f"  {p.name}")
    print(f"Flow diagram: {flow.name}")
    print(f"Terminal log: {term.name}")
    print(f"\nAll outputs under {OUT}/")


if __name__ == "__main__":
    main()
