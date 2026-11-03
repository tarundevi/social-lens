# CONTRACTS: frozen at minute 0

The lead (Track A owner) commits this as `contracts/` on `main` **before anyone branches**. After that it is frozen: changes need all track owners to agree, then a `contracts:` commit on main that everyone rebases onto. Every track stubs the others with these files, so each can run standalone.

## Files to create at minute 0 (copy the blocks below verbatim)
```
contracts/
├── fixtures/
│   ├── health.json            # GET /api/health
│   ├── session.json           # POST /api/sessions
│   ├── analyze_dinner.json    # POST /api/analyze response
│   ├── analyze_sarcasm.json
│   ├── analyze_wave.json
│   ├── analyze_none.json      # hud:null
│   ├── recap.json             # POST /api/recap response
│   └── ws_stream.jsonl        # WS messages, one per line, with "_delay_ms"
├── scenarios.json             # demo scenarios (Track D later owns data/scenarios.json with the same shape)
└── types.md                   # = the type blocks below
```
Schemas: `schemas/events.schema.json` (Graption v1.2, verbatim) and `schemas/social_cue.schema.json` (from docs/reference) are also committed at minute 0.

## Endpoints (full detail in API_SPEC.md)
`GET /api/health` · `POST /api/sessions` · `DELETE /api/sessions/{id}` · `POST /api/sessions/{id}/captions` · `POST /api/analyze` · `GET /api/sessions/{id}/events` · `WS /ws/sessions/{id}[?replay=1&speed=1]` · `POST /api/recap` · (stretch) `POST /api/stt`.
CORS: the backend allows `*` in dev so pages served from anywhere (and the iOS app) can call it.

## Shared types (TypeScript notation, for docs only)
```ts
type CueType = "question_to_you"|"sarcasm_or_joke"|"greeting_gesture"|"turn_taking"|"other"|"none";
interface SocialCueOutput { cue_type: CueType; cue: string; visual_evidence: string|null;
  audio_evidence: string|null; suggested_response: string|null; confidence: number; should_notify: boolean; }
interface SocialCueEvent extends SocialCueOutput { type: "social_cue"; session_id: string; schema_version: "1.2";
  cue_id: string; t: number; notified: boolean; speaker_id?: string; related_caption_id: string|null;
  source: "grok"|"canned"; input_kind: "live_camera"|"demo_input"|"glasses"|"audio_only"; model_version: string; }
interface AnalyzeRequest { session_id: string; t: number; transcript_window: string; image_b64?: string|null;
  scenario_id?: "dinner"|"sarcasm"|"wave"|null; input_kind?: SocialCueEvent["input_kind"]; }
interface DisplayNode { kind: "FlexBox"|"Text"|"Icon"; direction?: "row"|"column"; style?: "heading"|"body"|"meta";
  color?: "primary"|"secondary"; text?: string; name?: string; children?: DisplayNode[]; }
interface Hud { kind: string; text: string; reply: string|null; icon: string; color: string;
  priority: number; ttl_s: number; footnote: string; tree: DisplayNode; }
interface AnalyzeResponse { event: SocialCueEvent; hud: Hud|null; source: "grok"|"canned"; latency_ms: number; }
interface WsMessage { event: GraptionEvent | SocialCueEvent; hud: Hud|null; }   // server → client only
interface RecapResponse { source: "grok"|"heuristic"; recap: RecapOutput; message: string|null; }  // RecapOutput: PROMPTS.md
```
`hud` is `null` whenever `event.notified` is false.

## Fixture contents
`health.json`
```json
{"ok": true, "grok": "missing_key", "model": "grok-4.7"}
```
`session.json`
```json
{"session_id": "demo"}
```
`analyze_dinner.json`
```json
{"event":{"type":"social_cue","session_id":"demo","schema_version":"1.2","cue_id":"6f1c2a9e-1d3b-4c55-9a43-2b7f6f0e9a01","t":15.0,"cue_type":"question_to_you","cue":"They asked you to dinner Friday","visual_evidence":"Person facing you, open hand gesture toward you","audio_evidence":"\"Vaibhav, want to come to dinner Friday?\"","suggested_response":"I'd love to! What time?","confidence":0.92,"should_notify":true,"notified":true,"speaker_id":"unknown","related_caption_id":null,"source":"canned","input_kind":"demo_input","model_version":"canned-v0"},
 "hud":{"kind":"social_cue","text":"They asked you to dinner Friday","reply":"I'd love to! What time?","icon":"questionmark.bubble","color":"#4FC3F7","priority":3,"ttl_s":8,"footnote":"model guess",
  "tree":{"kind":"FlexBox","direction":"column","children":[{"kind":"Text","style":"heading","text":"They asked you to dinner Friday"},{"kind":"Text","style":"body","text":"Say: I'd love to! What time?"},{"kind":"Text","style":"meta","color":"secondary","text":"model guess"}]}},
 "source":"canned","latency_ms":12}
```
`analyze_sarcasm.json` / `analyze_wave.json`: same shape, using the PROMPTS.md few-shot B / C outputs, `cue_id` ending `...02` / `...03`, `t` 42.5 / 61.0, icons `face.smiling` / `hand.wave` (icon names are our own strings, not Meta's).
`analyze_none.json`: the few-shot D output wrapped as an event with `notified:false`, plus `"hud": null`.
`recap.json`
```json
{"source":"heuristic","message":"No XAI_API_KEY set; showing a rule-based summary, not Grok.",
 "recap":{"overall_summary":"Study group split the data structures project.","per_speaker":[{"speaker":"Sarah","summary":"Organized the split."}],
 "addressed_to_you":[{"t":"0:11","speaker":"Alex","quote":"Vaibhav, can you take the hash table section?","what_they_need":"Yes/no on owning hash tables"}],
 "action_items":[{"owner":"Vaibhav","item":"Hash table section","due":null}],
 "tone_highlights":[{"t":"1:40","speaker":"Priya","tone":"sounded frustrated?","note":"About the deadline"}],
 "disclaimer":"Tone highlights are model guesses about tone of voice, not feelings."}}
```
`ws_stream.jsonl`: 6 lines. A caption (Graption v1.2 `caption`, speaker_id "unknown"), then the dinner analyze `{event,hud}`, a `sound_event` doorbell 0.91 with a hud, the sarcasm `{event,hud}`, the wave `{event,hud}`, then a duplicate wave with `notified:false, hud:null`. Each line adds `"_delay_ms": 1500`.
`scenarios.json`
```json
[{"id":"dinner","title":"Dinner invite","image":"demo/dinner.jpg","transcript":["[0:10] Someone: hey","[0:12] Someone: Vaibhav, want to come to dinner Friday?"],"canned":"analyze_dinner.json"},
 {"id":"sarcasm","title":"Sarcasm","image":"demo/sarcasm.jpg","transcript":["[0:40] Someone: Oh great, another three-hour meeting."],"canned":"analyze_sarcasm.json"},
 {"id":"wave","title":"Wave greeting","image":"demo/wave.jpg","transcript":[],"canned":"analyze_wave.json"}]
```

## Mock mode (so frontends run without the backend)
- Every page accepts `?mock=1`. Then `fetch` reads `/contracts/fixtures/*.json` instead of `/api/*`, and the WS is replaced by replaying `ws_stream.jsonl` with `setTimeout(_delay_ms)`.
- Serve the repo root statically for mock mode: `python -m http.server 8080`, then open `http://localhost:8080/web/live.html?mock=1`.
- The backend (Track A) also serves `/contracts` statically, so mock mode works on :8000 too.
- iOS (Track E) can POST to the real backend, or read `analyze_*.json` from its bundle.
