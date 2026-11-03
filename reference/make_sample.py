"""Generate data/sample_session.jsonl: a ~2.5 min, 3-speaker Graption session (schema v1.2).

Deterministic (uuid5 ids, fixed probs) so the demo is identical every run.
Speaker display names live in data/speakers.json: Graption only knows face ids (f1, f2...).
"""
import json
import uuid
from pathlib import Path

SID = "demo-study-group"
NS = uuid.UUID("6f1c2a52-9b7e-4a8e-9a43-1f0e5f3c2d10")
ROOT = Path(__file__).resolve().parents[1]
MV = {"asr": "whisperkit-base.en", "asd": "largest-face-v0"}
EMO = ["anger", "disgust", "fear", "happy", "neutral", "sad"]

# (t_start, t_end, face, text, tone tag or None)
LINES = [
    (2.0, 6.1, "f1", "Okay, so the demo is Friday and we still don't have the tone chart working.", None),
    (6.8, 10.9, "f2", "I pushed a fix last night, but the WebSocket keeps dropping on campus Wi-Fi.", "sad"),
    (11.5, 15.2, "f3", "That's the eduroam thing again. We can run the tone server on a hotspot.", None),
    (16.0, 20.4, "f1", "Fine, but I really need someone to own the slides. I can't do everything.", "anger"),
    (21.1, 25.0, "f2", "I'll take the slides if Priya can handle the backend fixes.", None),
    (25.6, 28.9, "f3", "Yeah, I can do the backend. Should be a couple of hours.", "happy"),
    (29.5, 34.2, "f1", "Great. Vaibhav, can you send the user testing notes to everyone by Wednesday?", None),
    (35.0, 37.6, "f2", "And Vaibhav, did you book the room for Thursday?", None),
    (38.5, 42.0, "unknown", "Sorry, is anyone using this table? We were going to sit here.", None),
    (42.6, 45.3, "f3", "We're using it, sorry! Maybe try the second floor.", "happy"),
    (47.0, 51.8, "f1", "Anyway, the testers said captions were too small on the Pro Max.", None),
    (52.4, 56.9, "f2", "We could add a text size slider. It's like a ten minute change.", "happy"),
    (57.5, 62.3, "f3", "Wait, I think someone's at the door. Is that the pizza?", "fear"),
    (66.0, 70.4, "f2", "Pizza's here! Okay, okay, let's keep going while we eat.", "happy"),
    (71.0, 76.2, "f1", "The bigger issue is speaker detection. It keeps picking the largest face.", "sad"),
    (76.8, 81.5, "f3", "That's expected until the GRU model ships. Vision team said two weeks.", None),
    (82.0, 86.7, "f2", "Two weeks is after the demo though. That's honestly stressing me out.", "fear"),
    (87.3, 92.0, "f1", "Let's just say it out loud in the pitch. Judges like honesty about limits.", None),
    (92.8, 97.4, "f3", "Vaibhav, what do you think, should we demo on the glasses or the phone?", None),
    (100.5, 104.0, "f1", "Is that a siren? Hold on, let me close the window.", "fear"),
    (108.0, 112.6, "f2", "Okay. For the record, I vote phone for the demo and glasses for the roadmap.", None),
    (113.2, 118.0, "f3", "Agreed. And the dashboard summary is the part people will remember.", "happy"),
    (118.8, 123.5, "f1", "Then let's lock it. Alex on slides, Priya on backend, me on the dashboard.", "happy"),
    (124.2, 128.9, "f2", "One more thing, I'm out Thursday afternoon, so meet Thursday at six?", None),
    (129.5, 133.0, "f3", "Six works. Vaibhav, can you also bring the AirPods for the Subvox test?", None),
    (134.0, 138.6, "f1", "Perfect. I'm actually excited about this, it's coming together.", "happy"),
    (139.2, 143.0, "f2", "Same. Okay, I'm grabbing another slice. Good meeting.", "happy"),
]
SOUNDS = [(63.1, "doorbell", 0.91), (99.2, "siren", 0.84), (101.0, "siren", 0.88)]
BOXES = {"f1": [0.08, 0.30, 0.22, 0.30], "f2": [0.40, 0.28, 0.20, 0.28], "f3": [0.72, 0.32, 0.18, 0.26]}

def probs_for(tag, i):
    base = {e: 0.04 for e in EMO}
    base["neutral"] = 0.62
    if tag:
        base[tag] = 0.62
        base["neutral"] = 0.16
    # small deterministic wobble so the chart isn't flat
    base["happy"] += 0.02 * (i % 3)
    s = sum(base.values())
    return {e: round(v / s, 3) for e, v in base.items()}

def main():
    ev = []
    for i, (t0, t1, face, text, tag) in enumerate(LINES):
        cid = str(uuid.uuid5(NS, f"cap-{i}"))
        # a few speaker_scores frames per caption (real app: 15 fps; trimmed for size)
        for k in range(3):
            t = round(t0 + (t1 - t0) * (k + 0.5) / 3, 2)
            ev.append({"type": "speaker_scores", "session_id": SID, "schema_version": "1.2", "t": t,
                       "faces": [{"face_id": f, "p": (0.93 if f == face else 0.06), "bbox": b}
                                 for f, b in BOXES.items()]})
        ev.append({"type": "caption", "session_id": SID, "schema_version": "1.2", "caption_id": cid,
                   "t_start": t0, "t_end": t1, "text": text, "speaker_id": face, "model_versions": MV})
        tr = {"type": "tone_result", "session_id": SID, "schema_version": "1.2", "caption_id": cid,
              "tag": tag, "probs": probs_for(tag, i), "model_version": "tone-head-v2",
              "latency_ms": {"recv_to_send": 160 + 7 * (i % 5)}}
        ev.append(("_at", round(t1 + 0.4, 2), tr))  # tone arrives after caption
    for t, label, c in SOUNDS:
        ev.append({"type": "sound_event", "session_id": SID, "schema_version": "1.2", "t": t,
                   "label": label, "confidence": c})

    def at(e):
        if isinstance(e, tuple):
            return e[1]
        return e.get("t", e.get("t_end"))  # captions are emitted when the segment finishes
    out = sorted(ev, key=at)
    with open(ROOT / "data/sample_session.jsonl", "w") as f:
        for e in out:
            t = at(e)
            body = e[2] if isinstance(e, tuple) else e
            # _replay_t is a replay-only envelope field (when the phone would have emitted it);
            # it is stripped before validation and before sending over the wire.
            f.write(json.dumps({"_replay_t": t, "event": body}) + "\n")
    (ROOT / "data/speakers.json").write_text(json.dumps({
        "user_name": "Vaibhav",
        "speakers": {"f1": {"name": "Sarah", "color": "#4FC3F7"},
                     "f2": {"name": "Alex", "color": "#FFB74D"},
                     "f3": {"name": "Priya", "color": "#BA68C8"},
                     "unknown": {"name": "Someone", "color": "#9E9E9E"}}}, indent=2))
    print(f"wrote {len(out)} events")

if __name__ == "__main__":
    main()
