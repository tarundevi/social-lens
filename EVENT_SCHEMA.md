# Event schema

## Graption v1.2 (upstream, do not modify)
Source: `gt-big-data/graption/schemas/events.schema.json` (`$id .../schemas/events.schema.json`, title `GraptionEvent`, JSON Schema Draft 2020-12). Root is a `oneOf` of 7 event types. **Every event** requires `type`, `session_id` (string, minLength 1) and `schema_version` (const `"1.2"`), with `additionalProperties: false`. Times are **seconds since session start** (phone monotonic clock). `FaceId` = `^f[1-9][0-9]*$`.

| type | Key fields |
|---|---|
| `speaker_scores` | `t`, `faces[{face_id, p, bbox[4]}]` |
| `caption` | `caption_id` (uuid), `t_start`, `t_end`, `text`, `speaker_id` (FaceId or `"unknown"`), `model_versions{asr, asd}` |
| `sound_event` | `t`, `label` (allow-listed), `confidence` (≥ 0.7) |
| `tone_request` | `caption_id`, `t_start`, `t_end`, `sample_rate`, `audio_b64` (client → tone server) |
| `caption_log` | `caption`, `tone_tag` |
| `tone_result` | `caption_id`, `tag` (string or null), optional `probs{anger,disgust,fear,happy,neutral,sad}`, optional `scores{arousal,valence,dominance}`, `model_version`, `latency_ms{recv_to_send}` |
| `session_error` | `code`, `message`, `request`, `request_encoding`, `model_version` |

Graption rule: changing `schemas/` means bumping `schema_version`, regenerating Pydantic + Swift (quicktype) types, and tagging the lead. **We don't edit their file.** We ship an extension schema and propose it upstream as v1.3.

Note for UI copy: Graption's tone labels are *audio tone-of-voice model outputs*. Show them as "sounded frustrated? (model guess)", never "is angry".

## Proposed: `social_cue` (extension)
Full schema: `reference/social_cue.schema.json` (validated against the 4 examples in `reference/social_cue.examples.jsonl`).

| Field | Type | Notes |
|---|---|---|
| `type` | const `"social_cue"` | |
| `session_id`, `schema_version` | as base | `schema_version` stays `"1.2"` until merged (then `"1.3"`) |
| `cue_id` | uuid | server-generated |
| `t` | number ≥ 0 | seconds since session start, frame capture time |
| `cue_type` | enum | `question_to_you`, `sarcasm_or_joke`, `greeting_gesture`, `turn_taking`, `other`, `none` |
| `cue` | string ≤ 80 | one line, HUD-ready |
| `visual_evidence`, `audio_evidence` | string or null | what was seen or heard; gestures and scene only, no identity, no facial emotion |
| `suggested_response` | string or null ≤ 120 | |
| `confidence` | 0-1 | model self-report |
| `should_notify` | bool | model's opinion |
| `notified` | bool | server decision: `should_notify && confidence ≥ 0.6 && !duplicate` |
| `speaker_id` | FaceId or `"unknown"` | optional; `"unknown"` in browser live mode (no diarization) |
| `related_caption_id` | uuid or null | nearest caption, if any |
| `source` | `grok` or `canned` | canned = labeled demo output |
| `input_kind` | `live_camera`, `demo_input`, `glasses`, `audio_only` | |
| `model_version` | string | e.g. `grok-4.7`, `canned-v0` |

The model returns only the **SocialCueOutput** subset (PROMPTS.md). The server adds `type`, `session_id`, `schema_version`, `cue_id`, `t`, `notified`, `speaker_id`, `related_caption_id`, `source`, `input_kind` and `model_version`.

### Example
```json
{"type":"social_cue","session_id":"live-ab12cd34","schema_version":"1.2",
 "cue_id":"6f1c2a9e-1d3b-4c55-9a43-2b7f6f0e9a01","t":15.0,
 "cue_type":"question_to_you","cue":"They asked you to dinner Friday",
 "visual_evidence":"Person facing the camera, looking toward you",
 "audio_evidence":"\"Vaibhav, want to come to dinner Friday?\"",
 "suggested_response":"I'd love to! What time?","confidence":0.92,
 "should_notify":true,"notified":true,"speaker_id":"unknown",
 "related_caption_id":"0b8e3f52-5c1a-4f0e-8d0a-6c9a1e2b7c33",
 "source":"grok","input_kind":"live_camera","model_version":"grok-4.7"}
```
More (sarcasm, wave, a deduped wave with `notified:false`) are in `reference/social_cue.examples.jsonl`.

### Validation
`validate.py` dispatches on `type`: `social_cue` goes to `social_cue.schema.json`, everything else to `events.schema.json`. Use `jsonschema.Draft202012Validator(schema, format_checker=FormatChecker())`. The server validates each event before appending it; an invalid event is a bug (log the field, drop it).

### Upstream merge (post-hackathon)
Add `SocialCue` to `$defs` and the root `oneOf`, bump `SchemaVersion` const to `1.3`, regenerate types, then PR to main with ruff + pytest passing.
