# PRD: Graption SocialLens

## Problem
Group conversation is hard to follow when you can't hear it all (DHH) or can't easily read its unwritten signals (many autistic or socially anxious people). Captions tell you *what* was said. They don't tell you *that a question was aimed at you*, that a line was sarcastic, or that someone across the room is waving. Afterwards there's no easy way to catch up on what you missed.

## Users
1. **DHH Graption users (primary):** already rely on Graption's speaker-aware captions; need "you're being addressed" alerts, non-verbal context, and a recap.
2. **Social-cue users (secondary, opt-in):** autistic or socially anxious people who *choose* gentle cues and suggested replies. Co-designed framing: support, never scoring or "correcting" the user.

## Goals
- G1: In live mode, surface a correct, evidence-backed cue within ~5 s for the 3 demo scenarios.
- G2: Every cue is a schema-valid Graption-style event (`social_cue`) in the same log as captions.
- G3: A Recap dashboard turns the event log into a Grok "catch me up" summary.
- G4: The HUD view maps 1:1 to Meta Ray-Ban Display components, so porting is mechanical.
- G5: The demo works with no camera, no glasses and no API key (scripted demo mode, labeled).

## Non-goals (this hackathon)
Native iOS app; face recognition or identity; emotion inference from faces; storing frames or audio; multi-user accounts; production deployment; replacing Graption's on-device ASR/ASD models.

## Features and acceptance criteria
**F1 Live mode (browser, "phone/laptop camera" stand-in for glasses)**
- getUserMedia webcam + mic. A red "● Capturing: camera + mic" indicator is always visible while active. One Stop button ends capture and clears the buffers.
- Transcript: browser Web Speech API (`webkitSpeechRecognition`, Chrome) into a rolling 30 s window. Optional stretch: xAI STT via backend proxy.
- Every 3 s: JPEG frame (≤640 px wide, quality ~0.7) + transcript window → `POST /api/analyze`. Never more than one request in flight.
- AC: speaking "Vaibhav, want to come to dinner Friday?" to the camera shows a `question_to_you` cue + suggested reply within ~5 s. Frames are never written to disk (check: grep the server for file writes).

**F2 Demo mode (fallback, always works)**
- 3 scripted scenarios: (a) dinner-invite question, (b) sarcasm "Oh great, another three-hour meeting", (c) wave greeting. Each uses a placeholder image + scripted transcript, labeled **"DEMO INPUT"**.
- With a key: sends the demo inputs to Grok for real. Without a key: shows canned outputs labeled **"Canned example (no API key)"**.
- AC: all 3 scenarios produce a cue on screen with the network unplugged and no key.

**F3 HUD mock**
- ~600×600 dark panel styled like the Ray-Ban Display: icon + one-line cue (≤60 chars) + "Say: …" suggested reply + small "model guess" footnote. Fades out after its TTL.
- Cue → view-model mapping lives in ONE module (`cues`) whose output tree uses FlexBox/Text/Icon-style nodes (see GLASSES_INTEGRATION.md).
- AC: the HUD updates live from the same event stream as the dashboard; repeated cues are not re-shown (dedupe).

**F4 Recap / "Catch me up"**
- Loads a session event log (live session in memory, or `data/sample_session.jsonl`). Shows a speaker timeline with captions, a tone-over-time chart (from `tone_result.probs`), sound-event markers and social-cue markers.
- "Catch me up" → `POST /api/recap` → Grok structured JSON: overall summary, per-speaker summary, moments addressed to you, action items, tone highlights (labeled "model guesses").
- AC: valid JSON rendered within ~10 s with a key. Without a key, a clear message plus a labeled heuristic fallback.

**F5 Graption event integration**
- Proposed `social_cue` event (EVENT_SCHEMA.md) validated by JSON Schema, alongside unmodified Graption v1.2 events.
- AC: `python scripts/validate.py data/*.jsonl` passes; replay endpoint streams the log in real time like Graption's `scripts/replay_client.py`.

**F6 Glasses (stretch, one person, abandon at minute 30)**
- Meta DAT CameraAccess sample running with MockDeviceKit or real glasses; frames forwarded to `/api/analyze`. Cue spoken via phone TTS (Wayfarer has no display) or sent to MWDATDisplay (Display model).

## Judging-criteria mapping
| Criterion | How we score |
|---|---|
| 1. Creative and extensive use of Grok tools | Grok API vision + structured output (live cues), Grok API recap, optional Grok STT; GrokBot for research/planning (these docs); Cursor for building. Show all three. |
| 2. Understanding of social-good use case | DHH-first (Graption's users), opt-in neurodivergent mode, explicit privacy rules, "tone of voice, not emotions" framing |
| 3. Working demo and technical execution | Live mode + bulletproof demo mode; schema-validated events; real-time replay |
| 4. Usefulness and integration with project | Uses Graption's real event schema, fills its planned-but-unbuilt past-meetings dashboard, follows its "wearable replaces iPhone camera" seam |

## Success metrics (demo-day)
- 3/3 demo scenarios produce the intended `cue_type`.
- Live cue latency p50 ≤ 5 s (frame sent to cue shown).
- 0 duplicate notifications for the same situation within 20 s.
- 100% of logged events pass schema validation.
- Recap names every "addressed to you" moment in the sample session.

## Privacy and ethics (summary; see PRIVACY_ETHICS.md)
No face recognition. No emotion inference from faces ("tone of voice" only, from transcript or Graption's audio tone model). No retention of frames or audio. Visible capture indicator. Consent banner. Cues are suggestions, labeled as model guesses.
