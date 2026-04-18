"""CLI entrypoint: `cue enroll | run | list | delete <id> | seed <folder>`."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from cue import audio, db, demo_seed, enroll, note, recognize, sdk_bridge, summarize
from cue.config import DB_PATH, MATCH_THRESHOLD, ensure_data_dir


def _setup_logging(rehearsal: bool) -> None:
    level = logging.DEBUG if rehearsal else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _say(msg: str) -> None:
    print(msg, flush=True)


def cmd_enroll(_args) -> int:
    db.init_db(DB_PATH)
    person = enroll.run_enrollment(DB_PATH, on_status=_say)
    if person is None:
        _say("Enrollment failed.")
        return 1
    # Kick off optional Claude blurb in the background.
    if person.intro_text:
        summarize.enqueue_blurb(DB_PATH, person.id, person.intro_text)
    return 0


def cmd_list(_args) -> int:
    db.init_db(DB_PATH)
    people = db.all_people(DB_PATH)
    if not people:
        print("(no enrolled people)")
        return 0
    for p in people:
        last = time.strftime("%Y-%m-%d %H:%M", time.localtime(p.last_seen_at))
        print(
            f"#{p.id:<4} {p.name:<24} last_seen={last} matches={p.match_count}"
        )
    return 0


def cmd_delete(args) -> int:
    db.init_db(DB_PATH)
    db.delete_person(DB_PATH, args.id)
    print(f"deleted #{args.id}")
    return 0


def cmd_reenroll(args) -> int:
    """Replace a person's voiceprint with a fresh 10s capture.

    Preserves name, intro_text, brief, user_note, match_count. Useful for
    pre-pitch: seed rich context via scripts/seed_pitch_data.py, then
    re-enroll each real teammate to bind their actual voice to the row.
    """
    import numpy as np

    db.init_db(DB_PATH)
    people = {p.id: p for p in db.all_people(DB_PATH)}
    person = people.get(args.id)
    if person is None:
        print(f"no person with id={args.id}")
        return 1

    from cue import audio as _audio, embed as _embed
    from cue.config import ENROLL_SECONDS

    print(f"Re-enrolling #{person.id} {person.name}...", flush=True)
    print("Preparing models (first run takes ~30s)...", flush=True)
    _embed.embed(np.zeros(16_000, dtype=np.float32))

    print(f"Listening for {ENROLL_SECONDS:.0f}s — speak now...", flush=True)
    wav = _audio.record_fixed(ENROLL_SECONDS)
    print("Embedding voice...", flush=True)
    vec = _embed.embed(wav)
    db.set_embedding(DB_PATH, person.id, vec)
    print(f"Voiceprint updated for #{person.id} {person.name}")
    return 0


def cmd_brief(args) -> int:
    """Regenerate the Claude brief for a specific person (or everyone)."""
    import json as _json

    db.init_db(DB_PATH)
    people = db.all_people(DB_PATH)
    targets = people if args.id is None else [p for p in people if p.id == args.id]
    if not targets:
        print(f"no person with id={args.id}")
        return 1
    for p in targets:
        if not p.intro_text:
            print(f"#{p.id} {p.name}: no intro_text, skipping")
            continue
        brief = summarize.generate_brief(p.intro_text, p.user_note)
        if brief is None:
            print(f"#{p.id} {p.name}: brief unavailable (no intro_text)")
            continue
        db.set_brief(DB_PATH, p.id, _json.dumps(brief))
        print(f"#{p.id} {p.name}: {brief}")
    return 0


def cmd_seed(args) -> int:
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"not a directory: {folder}")
        return 1
    ids = demo_seed.seed_from_folder(DB_PATH, folder)
    print(f"seeded {len(ids)} people")
    return 0


def cmd_run(args) -> int:
    """Main recognition loop: bridge + mic + recognition thread."""
    db.init_db(DB_PATH)
    log = logging.getLogger("cue.run")
    echo_mode = bool(getattr(args, "echo", False))

    bridge = sdk_bridge.EvenBridge()
    bridge.start()

    # Shared state for double-tap note mode.
    loop_ref: dict = {}
    last_card_ts: dict = {"ts": 0.0}

    def on_tap(side: str, count: int) -> None:
        if side != "right":
            return
        if count == 1:
            log.info("temple single-tap: enroll")
            person = enroll.run_enrollment(DB_PATH, on_status=log.info)
            if person and person.intro_text:
                summarize.enqueue_blurb(DB_PATH, person.id, person.intro_text)
        elif count == 2:
            loop = loop_ref.get("loop")
            pid = loop.last_matched_id if loop else None
            if pid is None:
                log.info("double-tap ignored — no recent match")
                return
            if time.time() - last_card_ts["ts"] > note.NOTE_WINDOW_AFTER_MATCH_S:
                log.info("double-tap ignored — note window expired")
                return
            note.run_note(DB_PATH, pid, on_status=log.info)
        elif count == 3:
            cmd_list(args)

    bridge.on_temple_tap(on_tap)

    stop = {"flag": False}
    def handle_sigint(_sig, _frame):
        stop["flag"] = True
    signal.signal(signal.SIGINT, handle_sigint)

    with audio.MicStream() as mic:
        def segs():
            for seg in mic.iter_segments():
                if stop["flag"]:
                    break
                yield seg

        loop = recognize.RecognitionLoop(
            DB_PATH, bridge, segs(), threshold=MATCH_THRESHOLD, echo=echo_mode
        )
        loop_ref["loop"] = loop
        loop.start()
        log.info("cue running; Ctrl+C to exit")
        try:
            while not stop["flag"]:
                time.sleep(0.2)
        finally:
            loop.stop()
            bridge.stop()
    return 0


def main(argv: list[str] | None = None) -> int:
    ensure_data_dir()
    p = argparse.ArgumentParser(prog="cue")
    p.add_argument("--rehearsal", action="store_true", help="verbose logging")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("enroll", help="capture 10s, enroll a new person").set_defaults(
        func=cmd_enroll
    )
    run_p = sub.add_parser("run", help="run the recognition loop")
    run_p.add_argument(
        "--echo",
        action="store_true",
        help="transcribe every speech segment and show it on the HUD (debug)",
    )
    run_p.set_defaults(func=cmd_run)
    sub.add_parser("list", help="list enrolled people").set_defaults(func=cmd_list)

    d = sub.add_parser("delete", help="delete a person by id")
    d.add_argument("id", type=int)
    d.set_defaults(func=cmd_delete)

    s = sub.add_parser("seed", help="enroll from a folder of .wav files")
    s.add_argument("folder")
    s.set_defaults(func=cmd_seed)

    b = sub.add_parser(
        "brief",
        help="regenerate the Claude brief (headline/context/followup) for a person",
    )
    b.add_argument("id", nargs="?", type=int, default=None, help="person id (omit for all)")
    b.set_defaults(func=cmd_brief)

    r = sub.add_parser(
        "reenroll",
        help="replace voiceprint for an existing person (keeps name/brief/notes)",
    )
    r.add_argument("id", type=int, help="person id to re-enroll")
    r.set_defaults(func=cmd_reenroll)

    args = p.parse_args(argv)
    _setup_logging(args.rehearsal)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
