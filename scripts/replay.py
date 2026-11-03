"""Print a session log at real time, for debugging (events only, no audio).

Usage: python scripts/replay.py [file.jsonl] [--speed 2.0] [--types caption,social_cue]
Reads {"_replay_t": t, "event": {...}} rows (data/sample_session.jsonl) or bare events with t/t_end.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def mmss(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def when(row: dict[str, Any]) -> float:
    ev = row.get("event", row)
    return float(row.get("_replay_t", ev.get("t", ev.get("t_end", 0.0))))


def summary(ev: dict[str, Any]) -> str:
    kind = ev.get("type")
    if kind == "caption":
        return f"{ev['speaker_id']}: {ev['text']}"
    if kind == "tone_result":
        return f"tone {ev.get('tag')} (model guess) for {ev['caption_id'][:8]}"
    if kind == "sound_event":
        return f"SOUND {ev['label']} ({ev['confidence']:.2f})"
    if kind == "social_cue":
        flag = "" if ev.get("notified") else " [not notified]"
        return f"CUE {ev['cue_type']}: {ev['cue']}{flag} ({ev['source']})"
    if kind == "speaker_scores":
        top = max(ev["faces"], key=lambda f: f["p"]) if ev.get("faces") else None
        return f"active speaker {top['face_id']} p={top['p']}" if top else "no faces"
    return json.dumps(ev)[:120]


def replay(path: Path, speed: float, types: set[str] | None) -> None:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    rows.sort(key=when)
    start = time.monotonic()
    for row in rows:
        ev = row.get("event", row)
        if types and ev.get("type") not in types:
            continue
        t = when(row)
        delay = t / speed - (time.monotonic() - start)
        if delay > 0:
            time.sleep(delay)
        print(f"[{mmss(t)}] {ev.get('type'):<14} {summary(ev)}", flush=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="?", default=str(ROOT / "data/sample_session.jsonl"))
    ap.add_argument("--speed", type=float, default=1.0, help="2.0 = twice real time")
    ap.add_argument("--types", default="", help="comma-separated event types to show")
    args = ap.parse_args(argv)
    if args.speed <= 0:
        ap.error("--speed must be > 0")
    types = {t for t in args.types.split(",") if t} or None
    try:
        replay(Path(args.path), args.speed, types)
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
