# COMPUTER 2: Track B, live capture frontend (branch `c2/live`)
Owned: `web/live.html`, `web/live.js`, `web/api.js`. Assume: contracts/fixtures (mock mode), C3's `web/app.css` and `web/hud.js` export `renderHud(el, hud)` (until merged, render the hud's text plainly).
## Setup
```bash
gh repo clone <org>/graption-sociallens && cd graption-sociallens   # after the orchestrator pushes the minute-0 contract freeze
git checkout -b c2/live
python3 -m venv .venv && . .venv/bin/activate && pip install -e . 2>/dev/null || pip install fastapi "uvicorn[standard]" httpx jsonschema pytest python-dotenv
```
Read first: `CLAUDE.md`, `docs/CONTRACTS.md`, `docs/API_SPEC.md`, `docs/EVENT_SCHEMA.md`, `docs/PROMPTS.md`.
**Prefix every agent prompt with:** "Read CLAUDE.md and docs/CONTRACTS.md. Edit ONLY these paths: web/live.html, web/live.js, web/api.js. Do not touch contracts/, schemas/, PROGRESS.md. If a contract change is needed, stop and tell me."

## PR rules
- One PR per task (or per milestone if tasks are tiny). Title `[C2][TaskId] summary`. Use the PR template checklist and paste the acceptance-check output.
- Open the PR as soon as the check passes; don't batch. Target the next sync point (M30 / M55 / M70).
- After any merge to main: `git fetch && git rebase origin/main && git push -f` (your own branch only).
- Don't edit PROGRESS.md. Put "Done / Next / Blockers" in the PR body.

## Tasks
**B1 api.js + mock.** "web/api.js: functions health(), createSession(), deleteSession(id), postCaption(id,c), analyze(req), events(id), recap(id), openWs(id, onMsg). With ?mock=1, read /contracts/fixtures/*.json and replay ws_stream.jsonl using _delay_ms (see CONTRACTS.md Mock mode)."
Check: `python -m http.server 8080`, open /web/live.html?mock=1, and the console shows the health fixture.

**B2 Consent + indicator.** "live.html: consent screen, then getUserMedia video+audio preview labeled 'Phone/laptop camera (stand-in for glasses)'. A red '● Capturing camera + mic' badge is shown while tracks are live. Stop ends the tracks and the WS and offers Discard (deleteSession)."
Check: the badge is shown only while capturing; the camera light turns off after Stop.

**B3 Transcript.** "webkitSpeechRecognition continuous + interim; rolling 30 s window of finals formatted '[m:ss] Someone: text'; postCaption on each final. Feature-detect and show 'Use Chrome' otherwise."
Check: spoken words appear on screen in Chrome.

**B4 Frame loop.** "Every 3 s: canvas ≤ 640 px wide, JPEG 0.7, base64 without prefix, analyze({session_id,t,transcript_window,image_b64,input_kind:'live_camera'}). One in flight. Show a cue list + embedded HUD (renderHud if available) + latency_ms. Pass recent cues as context."
Check: in mock mode the fixture cues render; with the backend and a key, saying the dinner line shows question_to_you within ~5 s.

**B5 Polish.** "Error toasts (429 busy is silent; 5xx shows a message), 'Grok not configured, use Demo mode' when health.grok == missing_key, and a link to demo + recap pages."
Check: killing the backend mid-session shows an error, not a crash.

**B6 (stretch, only after M55) xAI STT.** Only if C1 ships /ws/stt. Message formats are UNVERIFIED, so read docs.x.ai first.

## Integration
M30: switch from mock to the real backend at :8000 (same api.js). M55: live test with a key together with C1.
