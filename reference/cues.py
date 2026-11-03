"""HUD cue generation: the ONE place that decides what the glasses show.

Input: Graption events (schema v1.2). Output: HudCue objects with a short text, an icon name and
a priority. `to_display_tree()` renders a cue as a small FlexBox/Text/Icon tree, the same component
vocabulary MWDATDisplay (Meta Ray-Ban Display) exposes, so porting is a 1:1 mapping in Swift/Kotlin.
The dict keys below are our own; check the real MWDATDisplay API before porting.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

MAX_TEXT = 60          # a HUD line must be glanceable
TONE_ICON = {"happy": "smile", "anger": "alert", "sad": "frown", "fear": "alert",
             "disgust": "frown", "excited": "smile", "upset": "alert", "calm": "dot"}
TONE_WORD = {"happy": "upbeat", "anger": "frustrated?", "sad": "down?", "fear": "worried?",
             "disgust": "put off?", "excited": "excited", "upset": "upset?", "calm": "calm"}
SOUND_ICON = {"doorbell": "bell", "siren": "siren", "fire_alarm": "siren", "smoke_detector": "siren",
              "knock": "door", "baby_crying": "baby", "dog_bark": "dog"}
URGENT_SOUNDS = {"siren", "fire_alarm", "smoke_detector", "glass_breaking"}


@dataclass
class HudCue:
    kind: str                 # "caption" | "addressed" | "tone" | "sound"
    text: str
    icon: str
    color: str
    priority: int             # 0 info, 1 notice, 2 urgent
    ttl_s: float = 4.0
    speaker: str | None = None
    caption_id: str | None = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["display"] = to_display_tree(self)
        return d


def _short(text: str, n: int = MAX_TEXT) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def is_addressed(text: str, user_name: str) -> bool:
    """Heuristic until Graption ships its 'talking to you' signal: name mentioned, or 'you' + '?'."""
    t = text.lower()
    if re.search(rf"\b{re.escape(user_name.lower())}\b", t):
        return True
    return False  # name-only for now (fewer false alarms); add "you + ?" or gaze later


class CueEngine:
    """Stateful: remembers captions so a late tone_result can update its caption's cue."""

    def __init__(self, speakers: dict, user_name: str):
        self.speakers = speakers
        self.user_name = user_name
        self.captions: dict[str, dict] = {}

    def _spk(self, face_id: str) -> dict:
        return self.speakers.get(face_id) or self.speakers.get("unknown") or {"name": "Someone", "color": "#9E9E9E"}

    def on_event(self, e: dict) -> list[HudCue]:
        t = e.get("type")
        if t == "caption":
            self.captions[e["caption_id"]] = e
            s = self._spk(e["speaker_id"])
            cues = [HudCue("caption", f"{s['name']}: {_short(e['text'], 48)}", "speech", s["color"], 0,
                           speaker=s["name"], caption_id=e["caption_id"])]
            if is_addressed(e["text"], self.user_name):
                cues.append(HudCue("addressed", f"{s['name']} is talking to you", "arrow", "#FFFFFF", 1,
                                   ttl_s=5.0, speaker=s["name"], caption_id=e["caption_id"],
                                   meta={"text": _short(e["text"], 80)}))
            return cues
        if t == "tone_result" and e.get("tag"):
            c = self.captions.get(e["caption_id"])
            s = self._spk(c["speaker_id"]) if c else {"name": "Someone", "color": "#9E9E9E"}
            word = TONE_WORD.get(e["tag"], e["tag"])
            return [HudCue("tone", f"{s['name']} sounds {word}", TONE_ICON.get(e["tag"], "dot"), s["color"], 0,
                           ttl_s=3.0, speaker=s["name"], caption_id=e["caption_id"],
                           meta={"tag": e["tag"], "model_guess": True})]
        if t == "sound_event":
            urgent = e["label"] in URGENT_SOUNDS
            return [HudCue("sound", e["label"].replace("_", " ").title(), SOUND_ICON.get(e["label"], "sound"),
                           "#FF5252" if urgent else "#FFD54F", 2 if urgent else 1, ttl_s=5.0,
                           meta={"confidence": e["confidence"]})]
        return []  # speaker_scores etc. don't produce cues on their own


def to_display_tree(cue: HudCue) -> dict:
    """Component tree for the glasses: Row(Icon, Column(Text title, Text detail?))."""
    children = [{"component": "Text", "text": cue.text, "style": {"color": cue.color, "size": "large" if cue.priority else "medium"}}]
    if cue.meta.get("text"):
        children.append({"component": "Text", "text": cue.meta["text"], "style": {"color": "#BBBBBB", "size": "small"}})
    if cue.meta.get("model_guess"):
        children.append({"component": "Text", "text": "tone is a model guess", "style": {"color": "#777777", "size": "small"}})
    return {"component": "FlexBox", "direction": "row", "gap": 12, "children": [
        {"component": "Icon", "name": cue.icon, "color": cue.color},
        {"component": "FlexBox", "direction": "column", "children": children}]}
