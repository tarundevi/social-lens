"""Labeled canned outputs for demo mode without an XAI_API_KEY (Track D).

Source of truth: data/scenarios.json (canned = SocialCueOutput, the model-output subset from
PROMPTS.md). The server wraps the output into a social_cue event exactly as it does a Grok reply,
just with source="canned" and model_version="canned-v0", so the UI can label it.
"""
from __future__ import annotations

import copy
import json
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
    """Just the SocialCueOutput for a scenario. None -> the 'none' output. Unknown id -> KeyError."""
    if scenario_id is None:
        return copy.deepcopy(NONE_OUTPUT)
    return copy.deepcopy(_load()[scenario_id]["canned"])


def get(scenario_id: str | None) -> dict[str, Any]:
    """SocialCueOutput + metadata for wrapping into a social_cue event.

    Returns {"output": SocialCueOutput, "source": "canned", "model_version": "canned-v0",
    "input_kind": "demo_input", "t": default seconds (or None), "transcript": [...], "label": str}.
    Unknown scenario_id raises KeyError.
    """
    row = _load()[scenario_id] if scenario_id is not None else {}
    return {
        "output": get_output(scenario_id),
        "source": SOURCE,
        "model_version": MODEL_VERSION,
        "input_kind": INPUT_KIND,
        "t": row.get("t"),
        "transcript": list(row.get("transcript", [])),
        "label": LABEL,
    }
