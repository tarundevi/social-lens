# CLAUDE.md / .cursorrules: Graption SocialLens

You are building a 90-minute hackathon MVP. Read docs/ARCHITECTURE.md, API_SPEC.md, EVENT_SCHEMA.md and PROMPTS.md before coding. Do one task from docs/TASKS.md at a time and run its Check.

## Stack
Python 3.11+, FastAPI, httpx (async), jsonschema, pytest. Frontend: plain HTML + vanilla JS in `web/`, no build step (Chart.js via CDN is allowed).

## Conventions
- All xAI calls live only in `app/grok.py`. Model from `XAI_MODEL` (default `grok-4.7`), base `https://api.x.ai/v1`.
- Use only the request formats in API_SPEC.md. **Do not invent API params or endpoints.** If unsure, stop and say so.
- Every event conforms to `schemas/events.schema.json` (v1.2, never edit it) or `schemas/social_cue.schema.json`. Validate before append. Times are seconds since session start.
- Prompts and output schemas live in `app/prompts.py`, copied from PROMPTS.md.
- Small functions, type hints, no new dependencies without asking.
- Every feature must work with no key (canned/heuristic, labeled).

## Guardrails (never violate)
- Never put `XAI_API_KEY` in frontend code, logs, or git. `.env` stays git-ignored.
- Never write camera frames, audio, or live transcripts to disk or logs.
- No face recognition, identity guessing, or emotion-from-face features. Use "tone of voice" wording and label model guesses.
- Capture indicator must be visible whenever getUserMedia tracks are live.
- Don't commit datasets, weights, recordings, or secrets (Graption rule).
- Don't touch the glasses/iOS track unless the task says so.
