"""Load a Graption session (JSONL of schema v1.2 events) and fold it into a view model."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_events(path: Path | None = None) -> list[tuple[float, dict]]:
    path = path or DATA / "sample_session.jsonl"
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            out.append((float(row["_replay_t"]), row["event"]))
    return out


def load_speakers() -> dict:
    return json.loads((DATA / "speakers.json").read_text())


def build_view(events: list[tuple[float, dict]]) -> dict:
    """Join captions with their tone_result (by caption_id); collect sound events."""
    captions, tones, sounds = {}, {}, []
    for _, e in events:
        if e["type"] == "caption":
            captions[e["caption_id"]] = e
        elif e["type"] == "tone_result":
            tones[e["caption_id"]] = e
        elif e["type"] == "sound_event":
            sounds.append(e)
    rows = []
    for cid, c in captions.items():
        t = tones.get(cid)
        rows.append({**c, "tone_tag": t["tag"] if t else None, "tone_probs": (t or {}).get("probs")})
    rows.sort(key=lambda r: r["t_start"])
    duration = max([r["t_end"] for r in rows] + [s["t"] for s in sounds] + [0])
    return {"session_id": rows[0]["session_id"] if rows else None, "duration": duration,
            "captions": rows, "sounds": sounds, **load_speakers()}
