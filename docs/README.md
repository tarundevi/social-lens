# Graption SocialLens: build docs

**Pitch.** Graption already captions conversations for Deaf and hard-of-hearing (DHH) users, showing who spoke, how they sounded, and important sounds. SocialLens adds a live, opt-in **social-cue copilot** on top. Every ~3 s it sends Grok a camera frame plus the last ~30 s of transcript. Grok returns one short, evidence-backed cue ("Sarah asked you a question", "that was probably sarcasm", "someone is waving at you") with a suggested reply. The cue shows on a Ray-Ban Display-shaped HUD (mocked in the browser for now). Every cue is logged as a Graption-style `social_cue` event next to `caption` / `tone_result` / `sound_event`, so a **Recap dashboard** can "catch you up" afterwards. Built for the BDBI x SpaceXSI Grokathon (90 min; judged on Grok tool use, social-good understanding, working demo, and integration with the BDBI project).

## Index
| Doc | What it's for |
|---|---|
| [PRD.md](PRD.md) | Problem, users, goals, features + acceptance criteria, judging map, metrics |
| [COMPARISON.md](COMPARISON.md) | SocialLens plan vs Graption Recap plan, and what we kept from each |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, data flow (mermaid), stack choice, directory layout |
| [API_SPEC.md](API_SPEC.md) | Backend endpoints, Grok request examples, env vars |
| [EVENT_SCHEMA.md](EVENT_SCHEMA.md) | Graption schema v1.2 summary + proposed `social_cue` extension |
| [PROMPTS.md](PROMPTS.md) | System prompts, output schemas, few-shots for the 3 demo scenarios |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | 90-minute timeline, owners, cutoff rules, definition of done |
| [TASKS/](TASKS/README.md) + [CONTRACTS.md](CONTRACTS.md) | 4-computer parallel plan: COMPUTER_1-4, ORCHESTRATOR, PROGRESS, PR template |
| [GLASSES_INTEGRATION.md](GLASSES_INTEGRATION.md) | Meta Wearables DAT path (verified names), stretch track |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 60-90 s demo, pitch, judge Q&A, how to show Grok tool use |
| [PRIVACY_ETHICS.md](PRIVACY_ETHICS.md) | Hard privacy rules and ethics framing |
| [AGENT_RULES.md](AGENT_RULES.md) | CLAUDE.md / .cursorrules content: conventions and guardrails |
| `reference/` | Unpolished snippets from an earlier starter (sample-data generator, schema validator, HUD cue module). Reference only. |

## Using these docs with an AI coding agent
1. Create the repo (see ARCHITECTURE.md layout). Copy `AGENT_RULES.md` to `CLAUDE.md` **and** `.cursor/rules/sociallens.mdc` (or `.cursorrules`).
2. Put this whole folder in the repo as `docs/`. Agents should read `AGENT_RULES.md`, `ARCHITECTURE.md`, `API_SPEC.md`, `EVENT_SCHEMA.md` and `PROMPTS.md` before writing code.
3. Work through `TASKS.md` in order, pasting one task at a time. Each task has an acceptance check; don't move on until it passes.
4. The Graption schema lives at https://github.com/gt-big-data/graption/blob/main/schemas/events.schema.json. Copy it in verbatim (T1); don't retype it.
5. Use GrokBot for research and planning, Cursor (with Grok models if available) for code, and the Grok API in the product. Screenshot each for the judges (DEMO_SCRIPT.md).

## Verification status (checked Nov 2, 2026)
- ✅ xAI: `grok-4.7` is the recommended general model and accepts image input via the Responses API (`POST https://api.x.ai/v1/responses`, `input_image` + `input_text`). Structured output works via `response_format` json_schema (Chat Completions) or `text.format` json_schema (Responses). Source: docs.x.ai models, image-understanding, structured-outputs pages.
- ✅ xAI speech-to-text exists: `POST https://api.x.ai/v1/stt` (multipart; `model=grok-voice-transcribe-2.0`) and streaming `wss://api.x.ai/v1/stt` (raw PCM frames, Bearer auth, which means a server-side proxy). Unverified: which browser `MediaRecorder` formats (webm/opus) REST accepts. Docs say "15 audio formats" without listing them in what I read.
- ✅ Meta DAT iOS names come from github.com/facebook/meta-wearables-dat-ios samples (v1.0.1, 2026-10-09). See GLASSES_INTEGRATION.md. Note: the repo README still says "developer preview" while the Meta FAQ says 1.0 is stable (rolling out from Sept 30, 2026).
- ⚠️ Unverified: whether the Responses API accepts `"store": false` exactly as OpenAI's does. xAI's docs only say to avoid storing history when sending images. Exact rate limits and latency of grok-4.7 vision. Graption has no LICENSE file in its repo.
- ⚠️ SocialLens system prompt: I didn't have the teammate's verbatim text, so PROMPTS.md reconstructs it from the plan's rules. Swap in the original if it differs.
