# PROGRESS (orchestrator-only file; computers report via PR descriptions)

Last updated: <HH:MM ET> by orchestrator · Minute: <n>/90

## Computer 1 (Track A: backend/Grok), branch `c1/backend`
| Task | Status | PR | Blocker | Updated |
|---|---|---|---|---|
| A1 scaffold + health | todo | | | |
| A2 Grok client | todo | | | |
| A3 store/dedupe/events | todo | | | |
| A4 API + WS (+ stub cues) | todo | | | |
| A5 recap API | todo | | | |
| A6 tests + latency | todo | | | |

## Computer 2 (Track B: live capture), branch `c2/live`
| Task | Status | PR | Blocker | Updated |
|---|---|---|---|---|
| B1 api.js + mock mode | todo | | | |
| B2 consent + capture indicator | todo | | | |
| B3 Web Speech transcript | todo | | | |
| B4 3 s frame loop + cue list | todo | | | |
| B5 polish (errors, Stop/discard) | todo | | | |
| B6 (stretch) xAI STT client | todo | | | |

## Computer 3 (Track C: HUD + recap), branch `c3/hud-recap`
| Task | Status | PR | Blocker | Updated |
|---|---|---|---|---|
| C1 app/cues.py + tests | todo | | | |
| C2 hud.html (mock) | todo | | | |
| C3 recap timeline + tone chart | todo | | | |
| C4 catch-me-up UI | todo | | | |
| C5 live HUD via real WS | todo | | | |

## Computer 4 (Track D: demo + data, then E: glasses), branches `c4/demo-data`, `c4/glasses`
| Task | Status | PR | Blocker | Updated |
|---|---|---|---|---|
| D1 data + placeholder images | todo | | | |
| D2 canned.py + validate.py | todo | | | |
| D3 demo.js (buttons) | todo | | | |
| D4 sample session + replay script | todo | | | |
| E1 CameraAccess running (mock/real) | todo | | | |
| E2 frames → /api/analyze, TTS | todo | | | |
| E3 (Display) MWDATDisplay cue | todo | | | |

Status values: todo · doing · PR open · changes requested · merged · cut.

## Sync points
- [ ] M0-8 contract freeze pushed; all 4 computers branched
- [ ] M30 Merge 1 (D→A→C→B); demo mode works on real backend; **E go/no-go:** ___
- [ ] M55 Merge 2; live mode with key; recap works
- [ ] M70 feature freeze; final merge
- [ ] M70-90 dry run with key ☐ and offline/no key ☐

## Integration status
| Check | Status | Notes |
|---|---|---|
| Demo mode end to end, no key | | |
| Live cue ≤ ~5 s with key | | |
| HUD mirrors live/demo via WS | | |
| Recap lists 4 "Vaibhav" moments | | |
| `python scripts/validate.py data/*.jsonl` | | |
| No key in browser / no frames on disk | | |
| Glasses | | |

## Open cross-track issues
| # | Issue | Owner | Status |
|---|---|---|---|
