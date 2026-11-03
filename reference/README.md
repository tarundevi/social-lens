# reference/: unpolished snippets (do not ship as-is)
From an earlier starter attempt. Copy or adapt; they're not tested as an app.
- `make_sample.py`: deterministic ~143 s, 3-speaker study-group session (27 captions, 81 speaker_scores, 27 tone_result, 3 sound_event); JSONL rows `{"_replay_t": t, "event": {...}}`. "Vaibhav" is addressed 4 times.
- `sample_session.jsonl`: output of the above (Graption v1.2 events only, no social_cue yet).
- `validate.py`: validates JSONL against Graption `events.schema.json` (Draft 2020-12 + FormatChecker). Extend it to route `type=="social_cue"` to `social_cue.schema.json`.
- `session.py`: load events/speakers; join captions to tone results by `caption_id`.
- `cues.py`: `HudCue` dataclass + `CueEngine` (caption/tone/sound → HUD cue) + `to_display_tree()` producing FlexBox/Text/Icon-shaped dicts. The dict keys are our own; only the component *names* mirror MWDATDisplay.
- `speakers.json`: face_id → name/color overlay (f1 Sarah, f2 Alex, f3 Priya). Dashboard-only, never sent to a model.
- `social_cue.schema.json` + `social_cue.examples.jsonl`: proposed event schema; examples validate.
Paths assume `schemas/events.schema.json` and `data/` at the repo root.
