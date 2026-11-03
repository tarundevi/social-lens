"""Prompt constants and output schemas (from PROMPTS.md)."""

from __future__ import annotations

SOCIALLENS_SYSTEM_PROMPT = """You are SocialLens, a discreet social-cue assistant inside Graption, a captioning app for Deaf and
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
- Output JSON only, matching the schema."""

RECAP_SYSTEM_PROMPT = """You write "catch me up" recaps for Graption, a captioning app for Deaf and hard-of-hearing users.
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
Only use facts from the log. Use "Someone" for unknown speakers. Times as m:ss."""

SOCIAL_CUE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "cue_type",
        "cue",
        "visual_evidence",
        "audio_evidence",
        "suggested_response",
        "confidence",
        "should_notify",
    ],
    "properties": {
        "cue_type": {
            "type": "string",
            "enum": [
                "question_to_you",
                "sarcasm_or_joke",
                "greeting_gesture",
                "turn_taking",
                "other",
                "none",
            ],
        },
        "cue": {"type": "string"},
        "visual_evidence": {"type": ["string", "null"]},
        "audio_evidence": {"type": ["string", "null"]},
        "suggested_response": {"type": ["string", "null"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "should_notify": {"type": "boolean"},
    },
}

RECAP_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "overall_summary",
        "per_speaker",
        "addressed_to_you",
        "action_items",
        "tone_highlights",
        "disclaimer",
    ],
    "properties": {
        "overall_summary": {"type": "string"},
        "per_speaker": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["speaker", "summary"],
                "properties": {
                    "speaker": {"type": "string"},
                    "summary": {"type": "string"},
                },
            },
        },
        "addressed_to_you": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["t", "speaker", "quote", "what_they_need"],
                "properties": {
                    "t": {"type": "string"},
                    "speaker": {"type": "string"},
                    "quote": {"type": "string"},
                    "what_they_need": {"type": "string"},
                },
            },
        },
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["owner", "item", "due"],
                "properties": {
                    "owner": {"type": "string"},
                    "item": {"type": "string"},
                    "due": {"type": ["string", "null"]},
                },
            },
        },
        "tone_highlights": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["t", "speaker", "tone", "note"],
                "properties": {
                    "t": {"type": "string"},
                    "speaker": {"type": "string"},
                    "tone": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
        "disclaimer": {"type": "string"},
    },
}

DISCLAIMER = "Tone highlights are model guesses about tone of voice, not feelings."
