# 90-minute implementation plan

> TODO: this per-role timeline predates the 4-computer split. The authoritative sync points are M0 contract freeze, M30, M55 and M70 in TASKS/README.md, with C1=A, C2=B, C3=C, C4=D+E.

Roles (3-4 people):
- **A, Backend/Grok:** FastAPI, grok.py, analyze, recap, dedupe.
- **B, Live web:** live.html capture, Web Speech, frame loop, demo mode.
- **C, HUD + Recap UI:** hud.html, recap.html, cues.py tree.
- **D, Glasses stretch + pitch** (or C doubles): DAT CameraAccess sample, demo script, slides. With only 3 people, D's glasses work is dropped and C owns the pitch.

| Time | A (backend) | B (live web) | C (HUD/recap) | D (stretch/pitch) |
|---|---|---|---|---|
| 0-10 | T0-T2: scaffold, schemas, `/api/health`, one curl to Grok with an image works | T5 skeleton: camera preview + capture indicator + consent | T8: HUD static layout with hard-coded cue | Clone DAT repo, open CameraAccess in Xcode, enable Developer mode in Meta AI app |
| 10-30 | T3-T4: `/api/analyze` (Grok + canned), dedupe, store, WS | T6: Web Speech transcript + 3 s frame loop → analyze | T9: cues.py tree + HUD subscribes to WS | Get MockDeviceKit or real glasses streaming frames in sample |
| **30** | **Checkpoint:** demo mode works end to end (no key) and live works with a key. **Glasses cutoff: if D has no frames by now, D drops it and joins pitch/testing.** |
| 30-55 | T10: `/api/recap` + heuristic fallback | T7: Demo-mode buttons + DEMO INPUT images + scenarios.json | T11: Recap page (timeline, tone chart, cue markers) | If alive: POST glasses frames to `/api/analyze`, TTS the cue |
| 55-70 | T12: tests + validate.py on all events; latency log | Polish live: spinner, errors, Stop/discard | T13: "Catch me up" UI + disclaimers | DEMO_SCRIPT dry run #1, screenshots of GrokBot/Cursor |
| **70** | **Feature freeze.** Bugs only. |
| 70-85 | Dry run ×2 on the demo laptop, with key and with Wi-Fi off. Fix only demo-breaking bugs. |
| 85-90 | Buffer. Demo mode open in a tab as backup. |

## Cutoff rules
- **Minute 30:** no glasses frames means abandon the glasses track (no exceptions). Live Grok not working means demo with canned + recap and keep debugging in parallel.
- **Minute 45:** xAI STT proxy not working means stay on Web Speech.
- **Minute 55:** recap Grok call failing means ship the heuristic fallback, labeled.
- **Minute 70:** feature freeze; no new dependencies after it.
- Anything that needs iOS signing on stage is a recorded video, not live.

## Definition of done (MVP)
1. `uvicorn app.main:app` starts; `/api/health` OK.
2. Demo mode: all 3 scenarios render a cue + suggested reply on the HUD with **no key and no network**, labeled canned.
3. Live mode: with a key, saying the dinner line to the laptop camera yields a `question_to_you` cue in ≤ ~5 s; capture indicator visible; Stop clears everything.
4. Every emitted event validates (`python scripts/validate.py`).
5. Recap of `sample` session shows timeline + "Catch me up" (Grok or labeled heuristic) listing all 4 "Vaibhav" moments.
6. No key in the browser (search the page source for `xai-`); no frames on disk.

## Stretch goals (only after DoD)
- xAI streaming STT through a backend WS proxy (`wss://api.x.ai/v1/stt`, PCM16 16 kHz).
- Glasses frames from the DAT sample → `/api/analyze`; cue spoken via iOS TTS on Wayfarer.
- Ray-Ban Display: send the cue as `FlexBox`/`Text` via MWDATDisplay.
- Grok voice output for the suggested reply (whisper in ear).
- Haptic or visual priority levels; per-user sensitivity slider.
