# COMPUTER 3: Track C, HUD + recap dashboard (branch `c3/hud-recap`)
Owned: `web/hud.html`, `web/hud.js`, `web/recap.html`, `web/recap.js`, `web/app.css`, `app/cues.py`, `tests/test_cues.py`. Assume: fixtures + `docs/reference/cues.py`, `docs/reference/sample_session.jsonl`, `docs/reference/speakers.json` (C4 ships the real data/ copies). Uses C2's `web/api.js` after M30; before that, an inline fetch of fixtures.
## Setup
```bash
gh repo clone <org>/graption-sociallens && cd graption-sociallens   # after the orchestrator pushes the minute-0 contract freeze
git checkout -b c3/hud-recap
python3 -m venv .venv && . .venv/bin/activate && pip install -e . 2>/dev/null || pip install fastapi "uvicorn[standard]" httpx jsonschema pytest python-dotenv
```
Read first: `CLAUDE.md`, `docs/CONTRACTS.md`, `docs/API_SPEC.md`, `docs/EVENT_SCHEMA.md`, `docs/PROMPTS.md`.
**Prefix every agent prompt with:** "Read CLAUDE.md and docs/CONTRACTS.md. Edit ONLY these paths: web/hud.html, web/hud.js, web/recap.html, web/recap.js, web/app.css, app/cues.py, tests/test_cues.py. Do not touch contracts/, schemas/, PROGRESS.md. If a contract change is needed, stop and tell me."

## PR rules
- One PR per task (or per milestone if tasks are tiny). Title `[C3][TaskId] summary`. Use the PR template checklist and paste the acceptance-check output.
- Open the PR as soon as the check passes; don't batch. Target the next sync point (M30 / M55 / M70).
- After any merge to main: `git fetch && git rebase origin/main && git push -f` (your own branch only).
- Don't edit PROGRESS.md. Put "Done / Next / Blockers" in the PR body.

## Tasks
**C1 cues.py.** "Adapt docs/reference/cues.py into app/cues.py exposing hud_for(event) -> Hud|None matching the CONTRACTS.md Hud type (tree of FlexBox/Text nodes), for social_cue (only if notified), sound_event, caption addressed to USER_NAME, and tone_result ('sounded X?' + 'model guess'). tests/test_cues.py compares to contracts/fixtures/analyze_dinner.json hud."
Check: `pytest tests/test_cues.py`.

**C2 HUD page.** "web/hud.js export renderHud(el, hud) drawing the tree recursively: a 600×600 black rounded panel, white text, heading/body/meta styles, fade after ttl_s. web/hud.html?session=ID subscribes to the WS (mock: replay ws_stream.jsonl)."
Check: hud.html?mock=1 shows dinner, doorbell, sarcasm and wave in sequence; the duplicate wave doesn't appear.

**C3 Recap page.** "recap.html?session=sample: speaker lanes (colors from speakers.json), tone-over-time chart from tone_result.probs (Chart.js CDN), sound and social_cue markers, a replay button (WS ?replay=1). Mock: load docs/reference/sample_session.jsonl."
Check: the sample renders; clicking a marker scrolls to its caption.

**C4 Catch me up.** "Button → recap(id); render the RecapOutput sections with 'Addressed to you' first, the source tag (Grok / Rule-based) and the disclaimer."
Check: renders contracts/fixtures/recap.json in mock mode, and the live response at M55.

**C5 Live wiring.** After M30: use web/api.js, open hud.html?session=<live id> next to live.html.
Check: cues mirror in both windows.

## Integration
Your `app/cues.py` is imported by C1, so merge C1 (the cues.py task) in the first PR, before M30.
