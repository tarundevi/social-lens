# Plan comparison: SocialLens vs Graption Recap

| | Teammate's **SocialLens** plan | Our **Graption Recap + glasses** plan | **Merged: Graption SocialLens** |
|---|---|---|---|
| Core idea | Live Grok multimodal social-cue copilot | Post-session dashboard + HUD cues from Graption events | Live cues **and** recap from one event log |
| Input | Camera frame every 2-3 s + rolling 30 s transcript | Graption caption/tone/sound events (replayed) | Both: browser camera/mic (live) or scripted replay (demo) |
| Grok use | Vision + JSON cue per frame | Structured "catch me up" summary | Both, plus GrokBot/Cursor in the build |
| Output | `{cue_type, cue, visual_evidence, audio_evidence, suggested_response, confidence, should_notify}` | Summary, per-speaker, addressed-to-you, action items, tone highlights | SocialLens JSON becomes a `social_cue` event; recap reads it |
| Platform | Native iOS + Meta CameraAccess sample in 75 min, phone fallback at min 20 | Web dashboard; glasses on roadmap | **Browser web app first**; glasses = one-person stretch track, cut at min 30 |
| Graption integration | Implicit | Explicit (schema v1.2, dashboard slot in repo) | Explicit: proposed `social_cue` schema extension |
| Privacy | Strong rules (no face rec, no face emotion, no retention, indicator) | Consent, "model guess" labels | All of SocialLens's rules, plus tone labeled as model guesses |
| Demo risk | High (iOS signing, SDK, glasses pairing in 75 min) | Low | Low: demo mode works offline with no key |

## Kept from SocialLens
- The live loop (frame every ~3 s + 30 s transcript → Grok vision → structured cue).
- The exact output fields, `should_notify`, and dedupe.
- Suggested responses.
- The 3 demo scenarios (dinner invite, sarcasm, wave).
- All privacy rules and the visible capture indicator.
- The idea of a hardware fallback, made stricter (glasses are a parallel stretch, cut at minute 30).

## Kept from Graption Recap
- Graption schema v1.2 as the backbone, with every cue an event in the same log.
- The Recap / "Catch me up" dashboard (fills Graption's planned past-meetings dashboard).
- HUD mock with a single cue module that maps to MWDATDisplay.
- Real-time replay of sample sessions.
- "Tone, not emotion" and "model guess" labeling.

## Dropped
- Native iOS as the main path: too risky for 90 min, and judges can't see iOS signing struggles.
- Face-based anything beyond "a person is waving" (gesture/scene, not identity or emotion).
