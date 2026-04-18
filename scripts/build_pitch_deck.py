"""Generate the Cue pitch deck as `docs/Cue-Pitch.pptx`.

Run:  .venv/bin/python scripts/build_pitch_deck.py
"""
from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT = Path(__file__).resolve().parent.parent / "docs" / "Cue-Pitch.pptx"

INK = RGBColor(0x0E, 0x0E, 0x0E)
BG = RGBColor(0xFA, 0xFA, 0xFA)
ACCENT = RGBColor(0x00, 0xB8, 0x6F)
MUTED = RGBColor(0x6B, 0x72, 0x80)
DARK = RGBColor(0x11, 0x18, 0x27)
HUD_BG = RGBColor(0x00, 0x00, 0x00)
HUD_FG = RGBColor(0x00, 0xE8, 0x3E)


def paint_bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_text(slide, x, y, w, h, text, *, size=28, bold=False, color=INK, align=PP_ALIGN.LEFT, font="Helvetica"):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = 0
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = font
    return box


def add_bullets(slide, x, y, w, h, items, *, size=20, color=INK):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    for i, text in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        r = p.add_run()
        r.text = "—  " + text
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.name = "Helvetica"
        p.space_after = Pt(8)
    return box


def hud_card(slide, x, y, w, h, title, lines):
    """Mock G2 HUD card (black / green monospace)."""
    rect = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))  # MSO_SHAPE.RECTANGLE
    rect.fill.solid()
    rect.fill.fore_color.rgb = HUD_BG
    rect.line.color.rgb = HUD_FG
    rect.line.width = Pt(1.5)
    tf = rect.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.15)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = title
    r.font.size = Pt(18); r.font.bold = True
    r.font.color.rgb = HUD_FG; r.font.name = "Menlo"
    for line in ["-" * 28, *lines]:
        pp = tf.add_paragraph()
        pp.alignment = PP_ALIGN.LEFT
        rr = pp.add_run(); rr.text = line
        rr.font.size = Pt(14); rr.font.color.rgb = HUD_FG
        rr.font.name = "Menlo"


def build() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # ---------- 1. Title ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s, DARK)
    add_text(s, 0.7, 2.5, 12, 1.5, "CUE", size=140, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    add_text(s, 0.7, 4.2, 12, 0.8, "Ambient social memory for the Even G2.", size=32, color=ACCENT)
    add_text(s, 0.7, 6.6, 12, 0.4, "Even Realities Builders' Day  ·  2026", size=14, color=MUTED)

    # ---------- 2. The hook ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s)
    add_text(s, 0.7, 0.6, 12, 0.5, "THE HOOK", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 1.1, 12, 2.5,
             '"I met 40 people today.\nI remember maybe 6 names."',
             size=56, bold=True)
    add_text(s, 0.7, 5.3, 12, 0.8, "That's not a me problem — it's an interface problem.", size=24, color=MUTED)

    # ---------- 3. The wedge ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s)
    add_text(s, 0.7, 0.6, 12, 0.5, "THE WEDGE", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 1.2, 12, 1.2,
             "Meta Ray-Bans remember faces.\nCue remembers people.",
             size=48, bold=True)
    # Two columns
    add_text(s, 0.7, 3.7, 5.5, 0.4, "Face-based (cameras)", size=16, bold=True, color=MUTED)
    add_bullets(s, 0.7, 4.1, 5.5, 3,
                ["Needs a camera on your face",
                 "Blocked from bars, hospitals, therapy offices",
                 "Records strangers without consent"])
    add_text(s, 7, 3.7, 5.5, 0.4, "Voice-based (Cue)", size=16, bold=True, color=ACCENT)
    add_bullets(s, 7, 4.1, 5.5, 3,
                ["Cameraless by physics — G2 has no lens",
                 "Works everywhere cameras can't",
                 "Only remembers people you chose to remember"])

    # ---------- 4. Live demo placeholder ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s, DARK)
    add_text(s, 0.7, 0.6, 12, 0.5, "LIVE DEMO", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 2.7, 12, 1.5, "[ Walk up. Speak. Card appears. ]",
             size=44, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), align=PP_ALIGN.CENTER)
    add_text(s, 0.7, 4.6, 12, 0.6,
             "Abhishek says one sentence.\nCue recognizes his voice. The HUD says: \"Ask about G2 BLE quirks.\"",
             size=20, color=ACCENT, align=PP_ALIGN.CENTER)

    # ---------- 5. What lands on the HUD ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s)
    add_text(s, 0.7, 0.6, 12, 0.5, "WHAT LANDS ON THE HUD", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 1.1, 12, 0.9, "One glanceable card. 576 x 288 pixels. Green on black.",
             size=20, color=MUTED)
    # Two mock HUD cards
    hud_card(s, 0.7, 2.3, 5.8, 3.5, "Abhishek Jaiswal",
             ["Infra eng, Cue co-builder",
              "Pairing on demo-seed script",
              "Ask how the script pairing w",
              "",
              "seen 8 min ago"])
    hud_card(s, 6.85, 2.3, 5.8, 3.5, "Priya Subramanian",
             ["PM design @ Acme, Q3 lead",
              "Owes you beta invite link",
              "Ask about onboarding friction",
              "",
              "seen 40 min ago"])
    add_text(s, 0.7, 6.2, 12, 0.5,
             "Name  ·  what they do  ·  last thing promised  ·  what to say next",
             size=16, color=MUTED, align=PP_ALIGN.CENTER)

    # ---------- 6. Architecture ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s)
    add_text(s, 0.7, 0.6, 12, 0.5, "HOW IT WORKS", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 1.1, 12, 0.9, "Local-first. Cameraless. Built in a day.", size=24, bold=True)
    lines = [
        "Phone mic     →  VAD segments speech",
        "Segment       →  Resemblyzer 256-d voiceprint",
        "Voiceprint    →  cosine match against SQLite (local, ~/.cue/people.db)",
        "Match         →  Claude Haiku writes a 3-line brief",
        "Brief         →  HUD card via Even Hub SDK",
    ]
    add_bullets(s, 0.7, 2.6, 12, 4,
                lines, size=22, color=INK)
    add_text(s, 0.7, 6.3, 12, 0.5,
             "No cloud sync. No camera. No face database. ≤1.5s median latency.",
             size=16, color=MUTED)

    # ---------- 7. Privacy ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s)
    add_text(s, 0.7, 0.6, 12, 0.5, "PRIVACY, BY DESIGN", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 1.2, 12, 1.4,
             "Cue only remembers people\nyou chose to remember.",
             size=44, bold=True)
    add_bullets(s, 0.7, 4.3, 12, 3, [
        "Explicit enrollment — no row is written without a temple tap",
        "Local-first — ~/.cue/people.db lives on your phone. One-tap delete.",
        "Cameraless by physics — the G2 has no lens. No face database exists.",
        "No network on the critical path. Claude used only for optional summaries.",
    ], size=20)

    # ---------- 8. Why it wins ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s)
    add_text(s, 0.7, 0.6, 12, 0.5, "WHY PEOPLE'S CHOICE", size=12, bold=True, color=ACCENT)
    add_text(s, 0.7, 1.2, 12, 1.0, "Cue is the room.", size=44, bold=True)
    add_bullets(s, 0.7, 2.8, 12, 4, [
        "Every judge forgot someone's name this week. Felt the micro-panic.",
        "Every audience member is re-living it as pre-seeded teammates walk up.",
        "Tagline repeats itself: \"Meta Ray-Bans remember faces. Cue remembers people.\"",
        "\"Quiet Tech\" rendered as product. Best Brand Fit fallback.",
    ], size=20)

    # ---------- 9. Close ----------
    s = prs.slides.add_slide(blank_layout)
    paint_bg(s, DARK)
    add_text(s, 0.7, 1.5, 12, 1.2,
             "Faces are data.",
             size=56, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), align=PP_ALIGN.CENTER)
    add_text(s, 0.7, 2.8, 12, 1.2,
             "People are memory.",
             size=56, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    add_text(s, 0.7, 4.6, 12, 0.8,
             "G2 is the first wearable quiet enough\nto hold the second one.",
             size=22, color=RGBColor(0xDD, 0xDD, 0xDD), align=PP_ALIGN.CENTER)
    add_text(s, 0.7, 6.6, 12, 0.4,
             "Thank you.  ·  github.com/abhishekj720/Cue-evenRealitiesG2",
             size=14, color=MUTED, align=PP_ALIGN.CENTER)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build()
