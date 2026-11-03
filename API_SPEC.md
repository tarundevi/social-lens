# API spec

Base: `http://localhost:8000`. JSON everywhere. The xAI key is **server-side only**: never send it to the browser.

## Env vars
| Var | Default | Notes |
|---|---|---|
| `XAI_API_KEY` | (none) | If unset: `/api/analyze` and `/api/recap` return labeled canned/heuristic output with `"source":"canned"` |
| `XAI_MODEL` | `grok-4.7` | Verified on docs.x.ai/docs/models as the recommended general model; it accepts image input |
| `XAI_BASE_URL` | `https://api.x.ai/v1` | |
| `XAI_STT_MODEL` | `grok-voice-transcribe-2.0` | Only for the optional STT proxy |
| `USER_NAME` | `Vaibhav` | Used for "talking to you" detection |
| `CUE_DEDUPE_WINDOW_S` | `20` | |

## Endpoints
### `GET /api/health`
`{"ok": true, "grok": "configured"|"missing_key", "model": "grok-4.7"}`

### `POST /api/sessions` → `{"session_id": "live-<uuid8>"}`
Creates an in-memory session. `DELETE /api/sessions/{id}` wipes it (the "Stop" button calls this when the user picks "discard").

### `POST /api/sessions/{id}/captions`
Browser speech results become Graption `caption` events (speaker unknown, since Web Speech has no diarization).
```json
// request
{"t_start": 12.1, "t_end": 14.0, "text": "Vaibhav, want to come to dinner Friday?"}
// response: the stored event (schema-valid Graption caption)
{"type":"caption","session_id":"live-ab12cd34","schema_version":"1.2","caption_id":"<uuid>",
 "t_start":12.1,"t_end":14.0,"text":"Vaibhav, want to come to dinner Friday?","speaker_id":"unknown",
 "model_versions":{"asr":"web-speech","asd":"none"}}
```

### `POST /api/analyze`
```json
// request
{"session_id":"live-ab12cd34","t":15.0,
 "transcript_window":"[0:12] Someone: Vaibhav, want to come to dinner Friday?",
 "image_b64":"<jpeg base64, no data: prefix>",      // omit for audio-only
 "scenario_id": null                               // "dinner"|"sarcasm"|"wave" in demo mode
}
// response
{"event": { /* social_cue event, see EVENT_SCHEMA.md */ },
 "hud": { /* cue view-model + display tree from cues.py, or null if not notified */ },
 "source": "grok"|"canned", "latency_ms": 2140}
```
Rules: max 1 in-flight call per session (return `429 {"error":"busy"}` otherwise). Image ≤ 1 MB. Never write image or transcript to disk or logs. If `scenario_id` is set and there's no key, return the canned output for that scenario.

### `POST /api/stt` (optional stretch)
Multipart `file` (short audio clip) → proxies to `POST https://api.x.ai/v1/stt` → `{"text": "..."}`. ⚠️ Unverified: whether browser `audio/webm;codecs=opus` is an accepted format. Test with curl first, and convert to WAV in-browser if not.

### `GET /api/sessions/{id}/events` → `{"events":[...]}` (for Recap)
`id = "sample"` loads `data/sample_session.jsonl`.

### `WS /ws/sessions/{id}?replay=1&speed=1.0`
Server pushes `{"event": {...}, "hud": {...}|null}` as events are appended. With `replay=1` it streams the stored/sample log in real time using `_replay_t` (like Graption `scripts/replay_client.py`, but events instead of WAV chunks).

### `POST /api/recap`
```json
// request
{"session_id":"sample"}
// response
{"source":"grok"|"heuristic","recap":{ /* RecapOutput, PROMPTS.md */ },
 "message": null | "No XAI_API_KEY set; showing a rule-based summary, not Grok."}
```

## Grok request examples (verified formats)
Vision + structured output via the **Responses API** (image format from docs.x.ai image-understanding; `text.format` json_schema from docs.x.ai structured-outputs):
```bash
curl https://api.x.ai/v1/responses \
  -H "Authorization: Bearer $XAI_API_KEY" -H "Content-Type: application/json" \
  -d '{
  "model": "grok-4.7",
  "store": false,
  "input": [
    {"role": "system", "content": "<SOCIALLENS_SYSTEM_PROMPT>"},
    {"role": "user", "content": [
      {"type": "input_image", "image_url": "data:image/jpeg;base64,<B64>", "detail": "low"},
      {"type": "input_text", "text": "Transcript (last 30s):\n[0:12] Someone: Vaibhav, want to come to dinner Friday?\nUser name: Vaibhav"}
    ]}
  ],
  "text": {"format": {"type": "json_schema", "name": "social_cue", "strict": true,
           "schema": <SocialCueOutput schema from PROMPTS.md>}}
}'
```
Python (httpx), parsing the output:
```python
r = httpx.post(f"{BASE}/responses", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=30)
r.raise_for_status()
data = r.json()
text = next(c["text"] for item in data["output"] if item.get("type") == "message"
            for c in item["content"] if c.get("type") == "output_text")
cue = json.loads(text)
```
Recap (text only) via **Chat Completions** with `response_format` (verified):
```json
{"model":"grok-4.7",
 "messages":[{"role":"system","content":"<RECAP_SYSTEM_PROMPT>"},{"role":"user","content":"<compact event log>"}],
 "response_format":{"type":"json_schema","json_schema":{"name":"recap","schema":<RecapOutput>,"strict":true}}}
```
→ `json.loads(resp["choices"][0]["message"]["content"])`.

Notes:
- xAI structured outputs: `additionalProperties` defaults to false; nullable = `{"type":["string","null"]}`; no `\b` in regex patterns.
- ⚠️ `"store": false`: xAI docs advise not storing history when sending images. Exact param support is unverified, so drop it if the API rejects it.
- ⚠️ `"detail": "low"` appears in xAI examples as `"high"`. Whether `"low"` is accepted is unverified, so omit it if it errors.
- Reasoning models can be slow, so use timeout ≥ 30 s for the live call and show a spinner. If p50 > 5 s, try a `grok-4.20-0309-non-reasoning` model ID from the models page (unverified whether it accepts images).
