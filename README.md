# Cue

Ambient social memory for the Even G2.

> Meta Ray-Bans remember faces. Cue remembers people.

The first time someone introduces themselves, you tap your right temple. Cue
captures a voiceprint + their intro. Weeks later, when their voice speaks
again, their card fades into your HUD — name, one-line intro, when you last
spoke — before you finish saying "hey."

Cameraless by design. Local-first. No cloud. No strangers.

---

## Architecture

Cue is a **hybrid**:

- **Python laptop app** — the heavy ML: microphone capture, VAD segmentation,
  Resemblyzer voice embeddings, Whisper STT, SQLite, optional Claude 6-word
  blurb.
- **React plugin** (reused from our Even Hub plugin project) — runs inside the
  Even app's WebView. Subscribes to real Even SDK events (temple taps, IMU) and
  renders the HUD card. Talks to Python over a local WebSocket.

The only module on the Python side that imports the Even SDK is `sdk_bridge.py`
— and even that is a WebSocket wrapper, not a direct SDK import. The Python
code never imports any Even package.

## Install

Python 3.11+ (tested on 3.12).

```bash
cd /Users/mohammadjaveedsanganakal/workplace/cue
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,blurb]"
```

First install pulls PyTorch, CTranslate2 (Whisper), Resemblyzer, silero-vad —
about ~1 GB. The initial `cue enroll` call downloads the Whisper model
(`tiny.en`, ~40 MB) and the Resemblyzer weights the first time they're used.

## Permissions (macOS)

Grant **microphone** access to your terminal (Settings → Privacy & Security →
Microphone). Without it, `sounddevice` opens but records silence.

## Pairing your G2

Follow the Even Hub SDK docs. Cue's critical path does not require paired
glasses — you can enroll and verify recognition using the CLI alone. The G2
HUD is how the card surfaces in production; during dev, the fake bridge in
`tests/` captures card pushes to memory.

## Commands

```bash
cue enroll                      # tap-free: capture 10s now, enroll a new person
cue list                        # list enrolled people
cue delete 3                    # delete person #3
cue seed tests/fixtures/        # enroll from <Name>.wav files
cue run                         # start bridge + mic + recognition loop
cue --rehearsal run             # verbose logging for the 8th-hour dry run
```

### `cue enroll` walkthrough

Run it. Say "Hi, I'm Priya, I lead platform at Acme Corp and we're working on
payments infra." Cue transcribes, regex-extracts "Priya," embeds the voice,
writes a row. The Claude blurb (if `ANTHROPIC_API_KEY` is set) updates the
row a second or two later in the background — it never blocks enrollment.

### `cue run` walkthrough

Starts the WebSocket bridge on `ws://127.0.0.1:8765`, opens the mic, segments
speech via silero-vad, embeds each ≥1s segment, matches against the DB, and
pushes a card to any connected React plugin. The plugin forwards temple-tap
and head-shake events back — single-tap right = enroll, double-tap right =
note on the last-matched person, triple-tap right = list.

## Privacy

- **Explicit enrollment only.** No row is written without a deliberate
  temple-tap. Background audio that doesn't match a row is embedded for
  matching only, then discarded.
- **Local-first.** `~/.cue/people.db` never leaves the laptop. No sync. No
  backup. `cue delete <id>` is final.
- **Cameraless.** The G2 has no camera; Cue cannot identify by face.
- **Network.** The only network call is the optional Claude blurb in
  `summarize.py`, and only if `ANTHROPIC_API_KEY` is set. Grep for `http`,
  `requests`, `urllib`, `anthropic` — the only hit under `cue/` is that one
  file.

## Layout

```
cue/
├── cue/
│   ├── config.py         # paths, thresholds, constants
│   ├── db.py             # SQLite schema + CRUD
│   ├── audio.py          # mic + VAD segmentation
│   ├── embed.py          # Resemblyzer wrapper
│   ├── stt.py            # faster-whisper + name regex
│   ├── match.py          # cosine matcher
│   ├── enroll.py         # enrollment FSM
│   ├── recognize.py      # recognition loop
│   ├── note.py           # post-match double-tap note
│   ├── hud.py            # Person → card formatter
│   ├── sdk_bridge.py     # WebSocket bridge to the React plugin
│   ├── summarize.py      # optional Claude 6-word blurb
│   ├── app.py            # CLI entrypoint
│   └── demo_seed.py      # enroll from <Name>.wav files
└── tests/
    ├── test_db.py
    ├── test_embed.py
    ├── test_match.py
    ├── test_enroll.py
    └── test_recognize_e2e.py
```

## Hackathon scope

Per the project doc, MVP is a tap-to-enroll + recognize + HUD-card pipeline.
Notes, Claude blurb, and seeding are polish. The pitch is two pre-seeded
teammates walking up mid-talk.

## Demo runbook (3 terminals)

Three things need to run at once: the Python app (mic + matcher), the React
plugin (WS client + HUD), and the Even simulator pointed at the plugin.

### Terminal A — Python side

```bash
cd /Users/mohammadjaveedsanganakal/workplace/cue
.venv/bin/python -m cue.app enroll     # capture 10s, enroll yourself
.venv/bin/python -m cue.app list       # confirm row written
.venv/bin/python -m cue.app run        # start the recognition loop + WS bridge
```

The `run` command opens the WebSocket bridge on `ws://127.0.0.1:8765`.

### Terminal B — plugin dev server

```bash
cd /Users/mohammadjaveedsanganakal/workplace/cue/cue_plugin
npm run dev
```

Vite prints a URL, usually `http://localhost:5173/`.

### Terminal C — simulator

```bash
evenhub-simulator http://localhost:5173
```

The simulator opens a WebView where the plugin runs. The plugin auto-connects
to the Python bridge on `ws://127.0.0.1:8765`. When Python recognizes a voice,
it pushes a `send_card` over WS → plugin calls `textContainerUpgrade` → card
lands on the HUD.

### Pre-seed for the pitch

Before the pitch, pre-enroll 3-4 teammates so the live stage moment is
recognition, not enrollment:

```bash
.venv/bin/python scripts/generate_fixtures.py Priya Daniel Sarah
# each teammate speaks 4s into your mic when prompted
.venv/bin/python -m cue.app seed tests/fixtures/
.venv/bin/python -m cue.app list
```

Then on stage, start `cue run` — as each pre-seeded teammate speaks, their
card fades onto the HUD.

## Event protocol (WebSocket bridge)

```
Python → React (commands)
  {"type": "send_card", "title": str, "lines": [str], "ttl_ms": int}
  {"type": "clear_card"}

React → Python (events)
  {"type": "temple_tap", "side": "left"|"right", "count": int}
  {"type": "head_shake"}
```

Count maps to gesture: 1 = single tap, 2 = double tap, 3 = swipe up (treated
as triple for the HUD list view shortcut).
