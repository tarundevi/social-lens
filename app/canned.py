"""Labeled canned outputs for demo mode without an XAI_API_KEY (Track D).

Source of truth: data/scenarios.json (canned = SocialCueOutput, the model-output subset from
PROMPTS.md). The server wraps the output into a social_cue event exactly as it does a Grok reply,
just with source="canned" and model_version="canned-v0", so the UI can label it.
"""
from __future__ import annotations

import copy
import json
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "data" / "scenarios.json"

SOURCE = "canned"
MODEL_VERSION = "canned-v0"
INPUT_KIND = "demo_input"
LABEL = "Canned example (no API key)"

# PROMPTS.md few-shot D: returned when there is no scenario_id (nothing worth interrupting for).
NONE_OUTPUT: dict[str, Any] = {
    "cue_type": "none",
    "cue": "No cue",
    "visual_evidence": "Two people talking to each other, not facing you",
    "audio_evidence": "Small talk not directed at you",
    "suggested_response": None,
    "confidence": 0.8,
    "should_notify": False,
}


@lru_cache(maxsize=1)
def _load() -> dict[str, dict[str, Any]]:
    rows = json.loads(SCENARIOS_PATH.read_text())
    return {row["id"]: row for row in rows}


def scenario_ids() -> list[str]:
    """Demo scenario ids in display order: ["dinner", "sarcasm", "wave"]."""
    return list(_load())


def scenarios() -> list[dict[str, Any]]:
    """All scenarios (id, title, image, transcript, t, fixture, canned), deep-copied."""
    return copy.deepcopy(list(_load().values()))


def get_output(scenario_id: str | None) -> dict[str, Any]:
    """Just the SocialCueOutput for a scenario. None/"none" -> the 'none' output. Unknown -> KeyError."""
    if scenario_id in (None, "none"):
        return copy.deepcopy(NONE_OUTPUT)
    return copy.deepcopy(_load()[scenario_id]["canned"])


def _event(output: dict[str, Any], t: float | None, session_id: str) -> dict[str, Any]:
    """Wrap a SocialCueOutput as a schema-valid social_cue event (fresh cue_id each call)."""
    return {
        "type": "social_cue", "session_id": session_id, "schema_version": "1.2",
        "cue_id": str(uuid.uuid4()), "t": float(t or 0.0), **output,
        "notified": bool(output["should_notify"] and output["confidence"] >= 0.6),
        "speaker_id": "unknown", "related_caption_id": None, "source": SOURCE,
        "input_kind": INPUT_KIND, "model_version": MODEL_VERSION,
    }


def get(scenario_id: str | None, session_id: str = "demo") -> dict[str, Any]:
    """Canned AnalyzeResponse-shaped dict (same keys as contracts/fixtures/analyze_*.json) + metadata.

    {"event": social_cue event, "hud": None (server builds it via app.cues.hud_for),
     "source": "canned", "latency_ms": 0,
     "output": SocialCueOutput, "model_version": "canned-v0", "input_kind": "demo_input",
     "t": default seconds or None, "transcript": [...], "label": "Canned example (no API key)"}
    scenario_id None or "none" -> the 'none' output. Unknown scenario_id raises KeyError.
    The server should still re-run dedupe and set its own t/session_id; these are defaults.
    """
    if scenario_id == "none":
        scenario_id = None
    row = _load()[scenario_id] if scenario_id is not None else {}
    output = get_output(scenario_id)
    return {
        "event": _event(output, row.get("t"), session_id),
        "hud": None,
        "source": SOURCE,
        "latency_ms": 0,
        "output": output,
        "model_version": MODEL_VERSION,
        "input_kind": INPUT_KIND,
        "t": row.get("t"),
        "transcript": list(row.get("transcript", [])),
        "label": LABEL,
    }
