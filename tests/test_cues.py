"""hud_for(event) against the Hud shape frozen in docs/CONTRACTS.md.

The expected Hud below is copied verbatim from CONTRACTS.md's analyze_dinner.json
fixture so this test has no dependency on a contracts/ directory existing on disk.
"""
from app.cues import hud_for

DINNER_EVENT = {
    "type": "social_cue", "session_id": "demo", "schema_version": "1.2",
    "cue_id": "6f1c2a9e-1d3b-4c55-9a43-2b7f6f0e9a01", "t": 15.0,
    "cue_type": "question_to_you", "cue": "They asked you to dinner Friday",
    "visual_evidence": "Person facing you, open hand gesture toward you",
    "audio_evidence": "\"Vaibhav, want to come to dinner Friday?\"",
    "suggested_response": "I'd love to! What time?", "confidence": 0.92,
    "should_notify": True, "notified": True, "speaker_id": "unknown",
    "related_caption_id": None, "source": "canned", "input_kind": "demo_input",
    "model_version": "canned-v0",
}

DINNER_HUD = {
    "kind": "social_cue", "text": "They asked you to dinner Friday",
    "reply": "I'd love to! What time?", "icon": "questionmark.bubble", "color": "#4FC3F7",
    "priority": 3, "ttl_s": 8, "footnote": "model guess",
    "tree": {"kind": "FlexBox", "direction": "column", "children": [
        {"kind": "Text", "style": "heading", "text": "They asked you to dinner Friday"},
        {"kind": "Text", "style": "body", "text": "Say: I'd love to! What time?"},
        {"kind": "Text", "style": "meta", "color": "secondary", "text": "model guess"},
    ]},
}


def test_social_cue_notified_matches_contract_fixture():
    hud = hud_for(DINNER_EVENT)
    assert hud == DINNER_HUD


def test_social_cue_not_notified_returns_none():
    event = dict(DINNER_EVENT, notified=False)
    assert hud_for(event) is None


def test_sound_event_doorbell():
    hud = hud_for({"type": "sound_event", "label": "doorbell", "confidence": 0.91})
    assert hud["text"] == "Doorbell"
    assert hud["priority"] == 1
    assert hud["color"] == "#FFD54F"


def test_sound_event_siren_is_urgent():
    hud = hud_for({"type": "sound_event", "label": "siren", "confidence": 0.88})
    assert hud["priority"] == 2
    assert hud["color"] == "#FF5252"


def test_caption_addressed_to_user_name():
    hud = hud_for({"type": "caption", "text": "Vaibhav, can you take the hash table section?"})
    assert hud is not None
    assert hud["kind"] == "caption"


def test_caption_not_addressed_returns_none():
    hud = hud_for({"type": "caption", "text": "I'll take the slides if Priya can handle the backend."})
    assert hud is None


def test_tone_result_with_tag():
    hud = hud_for({"type": "tone_result", "tag": "anger", "caption_id": "x"})
    assert hud["text"] == "Sounded frustrated?"
    assert hud["footnote"] == "model guess"


def test_tone_result_without_tag_returns_none():
    hud = hud_for({"type": "tone_result", "tag": None, "caption_id": "x"})
    assert hud is None


def test_unhandled_event_returns_none():
    assert hud_for({"type": "speaker_scores"}) is None
