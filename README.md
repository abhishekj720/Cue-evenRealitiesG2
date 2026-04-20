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

## Quick start (fresh clone)

Python 3.11+ (tested on 3.12). Native ARM Python strongly recommended on
Apple Silicon — x86 under Rosetta is 150× slower for Resemblyzer inference.

```bash
# 1. Clone and enter
git clone https://github.com/javeedsanganakal/even-realities-g2.git cue
cd cue

# 2. Python env (use Homebrew python@3.12 on Apple Silicon)
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip wheel
# numba + llvmlite need wheels (source build is broken on 3.12)
.venv/bin/pip install --only-binary=:all: "numba>=0.60" "llvmlite>=0.43"
.venv/bin/pip install -e ".[dev,blurb]"

# 3. Add your Anthropic API key (TODO)
cp .env.example .env
#   open .env and replace sk-ant-XXXX-REPLACE-ME with a real key from
#   https://console.anthropic.com/settings/keys
#   (needs credits in Plans & Billing to actually use /v1/messages)

# 4. Plugin deps
cd cue_plugin && npm install && cd ..

# 5. Simulator (one-time global install)
npm install -g @evenrealities/evenhub-simulator

# 6. Smoke-test
.venv/bin/pytest -q
# → expect "7 passed"
```

First install pulls PyTorch, CTranslate2 (Whisper), Resemblyzer, silero-vad —
about ~1 GB. The initial `cue enroll` call downloads the Whisper `tiny.en`
model (~40 MB) and Resemblyzer weights the first time they're used.

### First run — 3 terminals

```bash
# Terminal A — Python daemon (recognition + optional translation)
.venv/bin/python -m cue.app run --echo

# Terminal B — React plugin (Vite dev server)
cd cue_plugin && npm run dev

# Terminal C — G2 simulator pointing at the plugin
evenhub-simulator http://localhost:5173
```

Then tap/speak per the demo flow below. For live translation captions, swap
Terminal A to `cue.app translate --to Spanish` (or any language).

### Seed the 4 pitch personas

The enrollment DB (`~/.cue/people.db`) doesn't transfer via git. Re-seed on
any new machine:

```bash
.venv/bin/python scripts/seed_pitch_data.py --reset
.venv/bin/python -m cue.app list    # confirm 4 rows
.venv/bin/python -m cue.app brief   # populate Claude briefs (needs API key)
```

### Setup gotchas

| Symptom | Fix |
|---|---|
| `llvmlite` build fails | Run the `--only-binary=:all:` line above BEFORE `pip install -e` |
| Whisper / Resemblyzer extremely slow on M-series Mac | Your Python is Intel under Rosetta. Use `/opt/homebrew/bin/python3.12` (native ARM) |
| Mic permission denied | macOS → Settings → Privacy & Security → Microphone → enable your terminal app |
| `webrtcvad` import error about `pkg_resources` | `pip install "setuptools<81"` — modern setuptools dropped `pkg_resources` |
| Plugin stuck at `WS: connecting` | Python daemon not running, or Terminal A died. Restart it. |
| No card on HUD despite MATCH in log | Plugin WS connected to a dead bridge. Refresh the simulator window. |

### What does NOT transfer via git

- `~/.cue/people.db` — local voiceprints. Rebuild via `seed_pitch_data.py` or re-enroll.
- `.env` with your real API key. Copy `.env.example` → `.env` and paste your key.
- Downloaded ML weights. Auto-downloaded on first model use.
- `.venv/` and `cue_plugin/node_modules/`. Recreate via setup steps.

## Secrets handling

- `.env` is **gitignored**. The `.env.example` template in the repo contains
  a placeholder key only.
- No Anthropic key, GitHub token, or other credential is ever committed.
- If you accidentally commit `.env`, rotate the key at
  https://console.anthropic.com/settings/keys and `git filter-repo --invert-paths --path .env`.

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

Count maps to gesture: 1 = single tap, 2 = double tap, 3 = swipe up (treated
as triple for the HUD list view shortcut).
