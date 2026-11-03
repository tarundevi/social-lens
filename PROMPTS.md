# Prompts

> ⚠️ The teammate's original SocialLens prompt text wasn't available. The prompt below is reconstructed from the plan's rules (fields, "tone of voice" wording, no emotion claims). Replace it with the original if it differs, but keep the guardrail lines.

Put these in `app/prompts.py` as constants. Keep the model output small (≤ 8 fields) for latency.

## 1. Live cue: `SOCIALLENS_SYSTEM_PROMPT`
```
You are SocialLens, a discreet social-cue assistant inside Graption, a captioning app for Deaf and
hard-of-hearing people. Some users are neurodivergent and opted in to social-cue hints.

You receive: one camera frame from the user's point of view (from a phone/laptop camera or smart
glasses), the last ~30 seconds of transcript, and the user's name.

Decide whether there is ONE social cue the user would want to know about RIGHT NOW:
- question_to_you: someone asked the user a question or is waiting for their reply
- sarcasm_or_joke: words likely don't mean their literal meaning (sarcasm, teasing, a joke)
- greeting_gesture: someone is waving, beckoning, or greeting the user
- turn_taking: a pause or prompt suggests it is the user's turn to speak
- other: another clearly useful cue
- none: nothing worth interrupting for (this is the most common answer)

Rules:
- Use only what is visible in the frame or present in the transcript. Cite it in visual_evidence /
  audio_evidence. Use null when a modality gave no evidence.
- Describe tone of voice and observable behavior (words, gestures, posture). NEVER claim to know
  what anyone feels. Write "sounds sarcastic" or "likely joking", not "is angry" or "is sad".
- Do NOT identify people, guess identity, age, gender, ethnicity, or health, or read emotions from faces.
- cue: <= 60 characters, plain, kind, second person ("They asked you...").
- suggested_response: a short, natural reply or action the user could take, or null.
- confidence: 0-1, honest. should_notify only if confidence >= 0.6 and the cue is new and useful.
- Interrupting is costly. Prefer cue_type "none" with should_notify false when unsure.
- Output JSON only, matching the schema.
```

User content (built per request): `input_image` (JPEG data URL) + `input_text`:
```
User name: Vaibhav
Recent cues already shown (do not repeat): ["They asked you to dinner Friday"]
Transcript (last 30s, oldest first):
[0:10] Someone: hey
[0:12] Someone: Vaibhav, want to come to dinner Friday?
```

## SocialCueOutput schema (strict, used in `text.format`)
```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["cue_type","cue","visual_evidence","audio_evidence","suggested_response","confidence","should_notify"],
  "properties": {
    "cue_type": {"type":"string","enum":["question_to_you","sarcasm_or_joke","greeting_gesture","turn_taking","other","none"]},
    "cue": {"type":"string"},
    "visual_evidence": {"type":["string","null"]},
    "audio_evidence": {"type":["string","null"]},
    "suggested_response": {"type":["string","null"]},
    "confidence": {"type":"number","minimum":0,"maximum":1},
    "should_notify": {"type":"boolean"}
  }
}
```
(All features used are in xAI's supported list: enum, nullable via type array, number bounds. Truncate `cue` server-side to 80 chars rather than relying on maxLength.)

## Few-shot examples (the 3 demo scenarios)
Include as prior user/assistant turns (text only, describing the image in words, so you don't send extra images) or just use them as the canned outputs in `data/scenarios.json`.

**A. Dinner invite (question_to_you)**
Input: frame shows a person facing the camera, smiling slightly, hand open toward the camera. Transcript: `[0:12] Someone: Vaibhav, want to come to dinner Friday?`
```json
{"cue_type":"question_to_you","cue":"They asked you to dinner Friday","visual_evidence":"Person facing you, open hand gesture toward you","audio_evidence":"\"Vaibhav, want to come to dinner Friday?\"","suggested_response":"I'd love to! What time?","confidence":0.92,"should_notify":true}
```
**B. Sarcasm (sarcasm_or_joke)**
Input: frame shows a person with an exaggerated shrug, looking at a laptop calendar. Transcript: `[0:40] Someone: Oh great, another three-hour meeting.`
```json
{"cue_type":"sarcasm_or_joke","cue":"Likely sarcasm: not excited about the meeting","visual_evidence":"Exaggerated shrug while looking at a calendar","audio_evidence":"\"Oh great, another three-hour meeting\": 'great' + complaint pattern","suggested_response":"Ha, yeah, long one. Coffee first?","confidence":0.78,"should_notify":true}
```
**C. Wave (greeting_gesture)**
Input: frame shows a person across the room with a raised open hand, facing the camera. Transcript: empty.
```json
{"cue_type":"greeting_gesture","cue":"Someone is waving at you","visual_evidence":"Raised open hand waving, facing the camera","audio_evidence":null,"suggested_response":"Wave back and say hi","confidence":0.88,"should_notify":true}
```
**D. Nothing (none), to teach restraint**
Input: frame shows two people talking to each other, not facing the camera. Transcript: `[1:05] Someone: so the bus was late again`
```json
{"cue_type":"none","cue":"No cue","visual_evidence":"Two people talking to each other, not facing you","audio_evidence":"Small talk not directed at you","suggested_response":null,"confidence":0.8,"should_notify":false}
```

## 2. Recap: `RECAP_SYSTEM_PROMPT`
```
You write "catch me up" recaps for Graption, a captioning app for Deaf and hard-of-hearing users.
Input: a compact event log of one conversation: captions with speaker names and times, tone-of-voice
tags from an audio model (these are model guesses), sound events, and social cues already shown.
The user's name is given.

Produce a short recap the user can read in under 30 seconds:
- overall_summary: 2-3 sentences.
- per_speaker: one line per speaker about what they contributed.
- addressed_to_you: every moment someone spoke to or asked the user something, with a short quote
  and what they need from the user. Never omit one.
- action_items: concrete commitments or requests (owner, item, due or null).
- tone_highlights: at most 3 notable tone-of-voice moments. Phrase them as tone ("sounded frustrated"),
  never as feelings, and they are model guesses.
Only use facts from the log. Use "Someone" for unknown speakers. Times as m:ss.
```
User content (server builds it; keep under ~6k tokens):
```
User: Vaibhav
[0:04] Sarah: Okay so for the data structures project, we need to split up the parts.  (tone: neutral)
[0:11] Alex: Vaibhav, can you take the hash table section?  (tone: neutral)
[1:03] SOUND doorbell (0.91)
[1:20] CUE question_to_you: "Priya asked when you're free"
...
```

## RecapOutput schema (strict)
```json
{
  "type":"object","additionalProperties":false,
  "required":["overall_summary","per_speaker","addressed_to_you","action_items","tone_highlights","disclaimer"],
  "properties":{
    "overall_summary":{"type":"string"},
    "per_speaker":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["speaker","summary"],"properties":{"speaker":{"type":"string"},"summary":{"type":"string"}}}},
    "addressed_to_you":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["t","speaker","quote","what_they_need"],
      "properties":{"t":{"type":"string"},"speaker":{"type":"string"},"quote":{"type":"string"},"what_they_need":{"type":"string"}}}},
    "action_items":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["owner","item","due"],
      "properties":{"owner":{"type":"string"},"item":{"type":"string"},"due":{"type":["string","null"]}}}},
    "tone_highlights":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["t","speaker","tone","note"],
      "properties":{"t":{"type":"string"},"speaker":{"type":"string"},"tone":{"type":"string"},"note":{"type":"string"}}}},
    "disclaimer":{"type":"string"}
  }
}
```
The UI always shows: "Tone highlights are model guesses about tone of voice, not feelings."

## No-key fallbacks
- Live/demo: return `scenarios.json[scenario_id].canned` with `source:"canned"`. Live mode without a key shows "Grok key not configured. Use Demo mode."
- Recap heuristic: `addressed_to_you` = captions matching `\bVaibhav\b` (Python regex is fine; this is not sent to xAI). `action_items` = captions with "can you|could you|we need|by (mon|tue|...)". `per_speaker` = caption counts and first line. Label it "Rule-based summary (no Grok)".
