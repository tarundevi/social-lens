"""HUD cue view-model: the ONE place that turns a Graption/SocialLens event into a Hud.

Adapted from docs/reference/cues.py to match the Hud / DisplayNode shapes frozen in
docs/CONTRACTS.md. `hud_for(event)` returns a Hud dict or None when nothing should
be shown (e.g. a social_cue that wasn't notified, or a tone_result with no tag).
"""
from __future__ import annotations

import os
import re

MAX_TEXT = 60  # a HUD line must be glanceable
USER_NAME = os.environ.get("USER_NAME", "Vaibhav")

CUE_ICON = {
    "question_to_you": "questionmark.bubble",
    "sarcasm_or_joke": "face.smiling",
    "greeting_gesture": "hand.wave",
    "turn_taking": "arrow",
    "other": "bubble",
}
CUE_COLOR = {
    "question_to_you": "#4FC3F7",
    "sarcasm_or_joke": "#FFB74D",
    "greeting_gesture": "#81C784",
    "turn_taking": "#FFFFFF",
    "other": "#9E9E9E",
}
CUE_PRIORITY = {
    "question_to_you": 3,
    "sarcasm_or_joke": 2,
    "greeting_gesture": 2,
    "turn_taking": 1,
    "other": 1,
}
TONE_ICON = {"happy": "smile", "anger": "alert", "sad": "frown", "fear": "alert",
             "disgust": "frown", "excited": "smile", "upset": "alert", "calm": "dot"}
TONE_WORD = {"happy": "upbeat", "anger": "frustrated?", "sad": "down?", "fear": "worried?",
             "disgust": "put off?", "excited": "excited", "upset": "upset?", "calm": "calm"}
SOUND_ICON = {"doorbell": "bell", "siren": "siren", "fire_alarm": "siren", "smoke_detector": "siren",
              "knock": "door", "baby_crying": "baby", "dog_bark": "dog"}
URGENT_SOUNDS = {"siren", "fire_alarm", "smoke_detector", "glass_breaking"}


def _short(text: str, n: int = MAX_TEXT) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def is_addressed(text: str, user_name: str) -> bool:
    """Heuristic until Graption ships its 'talking to you' signal: name mentioned."""
    return bool(re.search(rf"\b{re.escape(user_name.lower())}\b", text.lower()))


def _tree(heading: str, body: str | None = None, meta: str | None = None) -> dict:
    children = [{"kind": "Text", "style": "heading", "text": heading}]
    if body:
        children.append({"kind": "Text", "style": "body", "text": body})
    if meta:
        children.append({"kind": "Text", "style": "meta", "color": "secondary", "text": meta})
    return {"kind": "FlexBox", "direction": "column", "children": children}


def _hud(kind: str, text: str, reply: str | None, icon: str, color: str,
         priority: int, ttl_s: float, footnote: str, tree: dict) -> dict:
    return {"kind": kind, "text": text, "reply": reply, "icon": icon, "color": color,
            "priority": priority, "ttl_s": ttl_s, "footnote": footnote, "tree": tree}


def hud_for(event: dict) -> dict | None:
    """Event (Graption v1.2 or social_cue) -> Hud dict, or None to show nothing."""
    t = event.get("type")

    if t == "social_cue":
        if not event.get("notified"):
            return None
        cue_type = event.get("cue_type", "other")
        text = _short(event["cue"])
        reply = event.get("suggested_response")
        body = f"Say: {reply}" if reply else None
        return _hud("social_cue", text, reply, CUE_ICON.get(cue_type, "bubble"),
                    CUE_COLOR.get(cue_type, "#9E9E9E"), CUE_PRIORITY.get(cue_type, 1),
                    8.0, "model guess", _tree(text, body, "model guess"))

    if t == "sound_event":
        label = event["label"]
        urgent = label in URGENT_SOUNDS
        text = label.replace("_", " ").title()
        return _hud("sound_event", text, None, SOUND_ICON.get(label, "sound"),
                    "#FF5252" if urgent else "#FFD54F", 2 if urgent else 1,
                    5.0, "", _tree(text))

    if t == "caption":
        if not is_addressed(event.get("text", ""), USER_NAME):
            return None
        text = f"{USER_NAME}, you're being addressed"
        detail = _short(event["text"], 80)
        return _hud("caption", text, None, "arrow", "#FFFFFF", 1, 5.0, "",
                    _tree(text, detail))

    if t == "tone_result":
        tag = event.get("tag")
        if not tag:
            return None
        word = TONE_WORD.get(tag, tag)
        text = f"Sounded {word}"
        return _hud("tone_result", text, None, TONE_ICON.get(tag, "dot"), "#BBBBBB",
                    0, 3.0, "model guess", _tree(text, None, "model guess"))

    return None  # speaker_scores etc. don't produce cues on their own
