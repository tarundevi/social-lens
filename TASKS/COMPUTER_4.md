# COMPUTER 4: Track D, demo mode + data, then Track E, glasses stretch (branches `c4/demo-data`, `c4/glasses`)
Owned: `data/`, `web/demo/`, `web/demo.js`, `app/canned.py`, `scripts/`, `tests/test_schema.py`, and `ios/` (Track E). Assume: contracts, schemas, docs/reference/*. Lightest load, so you also take glasses unless the orchestrator reassigns them.
## Setup
```bash
gh repo clone <org>/graption-sociallens && cd graption-sociallens   # after the orchestrator pushes the minute-0 contract freeze
git checkout -b c4/demo-data
python3 -m venv .venv && . .venv/bin/activate && pip install -e . 2>/dev/null || pip install fastapi "uvicorn[standard]" httpx jsonschema pytest python-dotenv
```
Read first: `CLAUDE.md`, `docs/CONTRACTS.md`, `docs/API_SPEC.md`, `docs/EVENT_SCHEMA.md`, `docs/PROMPTS.md`.
**Prefix every agent prompt with:** "Read CLAUDE.md and docs/CONTRACTS.md. Edit ONLY these paths: data/, web/demo/, web/demo.js, app/canned.py, scripts/, tests/test_schema.py, ios/. Do not touch contracts/, schemas/, PROGRESS.md. If a contract change is needed, stop and tell me."

## PR rules
- One PR per task (or per milestone if tasks are tiny). Title `[C4][TaskId] summary`. Use the PR template checklist and paste the acceptance-check output.
- Open the PR as soon as the check passes; don't batch. Target the next sync point (M30 / M55 / M70).
- After any merge to main: `git fetch && git rebase origin/main && git push -f` (your own branch only).
- Don't edit PROGRESS.md. Put "Done / Next / Blockers" in the PR body.

## Tasks (Track D, finish by M30)
**D1 Data.** "Copy docs/reference/{make_sample.py,validate.py} to scripts/, speakers.json and sample_session.jsonl to data/. Create data/scenarios.json (same shape as contracts/scenarios.json, with the canned outputs inlined from contracts/fixtures). Generate web/demo/{dinner,sarcasm,wave}.jpg with PIL: simple drawn figures plus a big 'DEMO INPUT' label, no real photos."
Check: files exist; images show the label.

**D2 canned + validate.** "app/canned.py: get(scenario_id) -> SocialCueOutput + metadata from data/scenarios.json. scripts/validate.py dispatches social_cue to schemas/social_cue.schema.json. tests/test_schema.py validates data/*.jsonl + docs/reference/social_cue.examples.jsonl."
Check: `pytest tests/test_schema.py`; `python scripts/validate.py data/sample_session.jsonl` gives 0 invalid.

**D3 demo.js.** "web/demo.js exports mountDemo(el, api): 3 buttons; each shows its image with the DEMO INPUT watermark, types out the transcript, then api.analyze({scenario_id, image_b64 if health.grok==configured, input_kind:'demo_input'}); a 'Canned example (no API key)' tag when source==canned." (C2 imports it on live.html after M30.)
Check: works in ?mock=1 and against the backend with no key and Wi-Fi off.

**D4 Sample with cues + replay.** "Extend make_sample.py to add 3 social_cue events (dinner-like question to Vaibhav, a sarcasm line, a wave) and a scripts/replay.py that prints events at real time for debugging."
Check: validate.py passes; regenerated data/sample_session.jsonl is deterministic.

## Track E (glasses), start after D2 is merged; hard go/no-go at M30
Follow docs/GLASSES_INTEGRATION.md. Branch `c4/glasses`, all code in `ios/`.
**E1** "Copy the meta-wearables-dat-ios samples/CameraAccess into ios/, enable Developer mode (Meta AI app), and run with MockDeviceKit or real glasses." Check: frames are visible in the app. **If not by M30, stop; mark it cut.**
**E2** "Every 3 s, decode a frame (sample's VideoFrameDecoder) → JPEG → POST http://<laptop-ip>:8000/api/analyze with input_kind 'glasses'; speak hud.text via AVSpeechSynthesizer." Check: a cue is spoken.
**E3 (Display only)** "Send hud.tree as FlexBox/Text via session.addDisplay() / display.send()." Check: the cue shows on the display.
Demo fallback for E: a screen recording, not live.
