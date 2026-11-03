# COMPUTER 1: Track A, backend + Grok (branch `c1/backend`)
Owned: `app/` except `app/cues.py` and `app/canned.py`; `pyproject.toml`, `.env.example`, `tests/test_api.py`, `tests/test_dedupe.py`, `tests/test_grok.py`. Assume: contracts/fixtures, schemas. Depends on: C3's `app/cues.py` (stub until M30), C4's `app/canned.py` + `data/scenarios.json` (until merged, fall back to `contracts/fixtures/analyze_*.json`).
## Setup
```bash
gh repo clone <org>/graption-sociallens && cd graption-sociallens   # after the orchestrator pushes the minute-0 contract freeze
git checkout -b c1/backend
python3 -m venv .venv && . .venv/bin/activate && pip install -e . 2>/dev/null || pip install fastapi "uvicorn[standard]" httpx jsonschema pytest python-dotenv
```
Read first: `CLAUDE.md`, `docs/CONTRACTS.md`, `docs/API_SPEC.md`, `docs/EVENT_SCHEMA.md`, `docs/PROMPTS.md`.
**Prefix every agent prompt with:** "Read CLAUDE.md and docs/CONTRACTS.md. Edit ONLY these paths: app/ (not cues.py, canned.py), pyproject.toml, .env.example, tests/test_api.py, tests/test_dedupe.py, tests/test_grok.py. Do not touch contracts/, schemas/, PROGRESS.md. If a contract change is needed, stop and tell me."

## PR rules
- One PR per task (or per milestone if tasks are tiny). Title `[C1][TaskId] summary`. Use the PR template checklist and paste the acceptance-check output.
- Open the PR as soon as the check passes; don't batch. Target the next sync point (M30 / M55 / M70).
- After any merge to main: `git fetch && git rebase origin/main && git push -f` (your own branch only).
- Don't edit PROGRESS.md. Put "Done / Next / Blockers" in the PR body.

## Tasks
**A1 Scaffold.** "Create pyproject (fastapi, uvicorn[standard], httpx, jsonschema, pytest, python-dotenv), .env.example (XAI_API_KEY=, XAI_MODEL=grok-4.7, USER_NAME=Vaibhav), app/main.py with GET /api/health per API_SPEC, static mounts for /web and /contracts, and CORS *."
Check: `uvicorn app.main:app` then `curl :8000/api/health` matches contracts/fixtures/health.json shape.

**A2 Grok client.** "app/grok.py + app/prompts.py per API_SPEC.md 'Grok request examples' and PROMPTS.md: analyze_frame() via POST /responses with input_image + input_text + text.format json_schema (SocialCueOutput); recap() via chat/completions response_format json_schema. Parse output item type message → output_text. 30 s timeout. GrokUnavailable when no key. Never log the key, images or transcripts. tests/test_grok.py mocks httpx."
Check: `pytest tests/test_grok.py`; with a key, a smoke script on any JPEG returns valid JSON. If `store` or `detail` are rejected (UNVERIFIED params), remove them.

**A3 Store/dedupe/events.** "app/store.py (in-memory sessions + asyncio broadcast), app/dedupe.py (same cue_type + token-Jaccard > 0.6 within 20 s; cue_type none is never notified; notified = should_notify && conf ≥ 0.6 && !dup), app/events.py make_social_cue() validating against schemas/social_cue.schema.json."
Check: `pytest tests/test_dedupe.py` (repeat wave suppressed, new question shown).

**A4 Endpoints + WS.** "Implement sessions, captions, analyze, events, WS /ws/sessions/{id}[?replay=1] exactly per API_SPEC/CONTRACTS. 429 if analyze is in flight. No key → canned via `app.canned.get(scenario_id)` (try-import; fall back to contracts/fixtures). hud via `app.cues.hud_for(event)` (try-import; fallback stub returns the fixture-shaped hud). Broadcast {event,hud}."
Check: the curl in docs/API_SPEC.md for analyze with scenario_id=wave returns a schema-valid event; repeating it within 20 s gives notified:false, hud:null.

**A5 Recap.** "POST /api/recap: build the compact log (PROMPTS.md format), call grok.recap; on no key or error, heuristic per PROMPTS.md, source='heuristic'."
Check: `curl -XPOST :8000/api/recap -d '{"session_id":"sample"}' -H 'content-type: application/json'` lists 4 Vaibhav moments (after C4's data is merged).

**A6 Tests + latency.** "tests/test_api.py with TestClient for health, analyze (canned), recap (heuristic); log analyze latency p50/p95 to stdout only."
Check: `pytest -q` green.

## Integration
At M30, after C4 is merged: remove the fallback paths only if `app.canned`/`app.cues` exist. At M55: real key test with C2's live page.
