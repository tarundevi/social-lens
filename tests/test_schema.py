"""Track D: every shipped event / canned output is schema-valid."""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import validate  # noqa: E402  (scripts/validate.py)
from app import canned  # noqa: E402

CHECKER = validate.Checker()
DATA_FILES = sorted((ROOT / "data").glob("*.jsonl"))
CUE_EXAMPLES = [p for p in (ROOT / "reference" / "social_cue.examples.jsonl",
                            ROOT / "docs" / "reference" / "social_cue.examples.jsonl") if p.is_file()]


def test_schemas_found() -> None:
    assert CHECKER.cue is not None, "social_cue.schema.json missing from schemas/ and reference/"


@pytest.mark.parametrize("path", DATA_FILES + CUE_EXAMPLES, ids=lambda p: p.name)
def test_jsonl_valid(path: Path) -> None:
    res = validate.validate_file(path, CHECKER)
    assert res["invalid"] == []
    if res["unchecked"]:
        pytest.skip(f"{res['unchecked']} Graption events unchecked: schemas/events.schema.json missing")


def test_cue_examples_found() -> None:
    assert CUE_EXAMPLES, "social_cue.examples.jsonl not found"


def _as_event(scenario_id: str | None) -> dict:
    c = canned.get(scenario_id)
    out = c["output"]
    return {"type": "social_cue", "session_id": "demo", "schema_version": "1.2",
            "cue_id": str(uuid.uuid4()), "t": c["t"] or 0.0, **out,
            "notified": out["should_notify"] and out["confidence"] >= 0.6,
            "speaker_id": "unknown", "related_caption_id": None, "source": c["source"],
            "input_kind": c["input_kind"], "model_version": c["model_version"]}


@pytest.mark.parametrize("scenario_id", ["dinner", "sarcasm", "wave", None, "none"])
def test_canned_wraps_into_valid_social_cue(scenario_id: str | None) -> None:
    assert CHECKER.errors(_as_event(scenario_id)) == []
    assert CHECKER.errors(canned.get(scenario_id)["event"]) == []


def test_canned_matches_backend_fixture_shape() -> None:
    """app/main.py get_canned() reads canned["event"] and canned.get("hud") like a fixture."""
    c = canned.get("wave")
    assert {"event", "hud", "source", "latency_ms"} <= set(c)
    assert c["event"]["cue"] == "Someone is waving at you" and c["event"]["notified"] is True
    assert c["event"]["cue_id"] != canned.get("wave")["event"]["cue_id"]
    assert canned.get("none")["event"]["notified"] is False


def test_canned_metadata() -> None:
    assert canned.scenario_ids() == ["dinner", "sarcasm", "wave"]
    c = canned.get("dinner")
    assert c["source"] == "canned" and c["model_version"] == "canned-v0"
    assert c["output"]["cue_type"] == "question_to_you"
    assert set(c["output"]) == {"cue_type", "cue", "visual_evidence", "audio_evidence",
                                "suggested_response", "confidence", "should_notify"}
    assert canned.get(None)["output"]["should_notify"] is False
    with pytest.raises(KeyError):
        canned.get("nope")


def test_canned_returns_copies() -> None:
    canned.get("wave")["output"]["cue"] = "mutated"
    assert canned.get("wave")["output"]["cue"] == "Someone is waving at you"


def test_scenario_images_exist() -> None:
    for s in canned.scenarios():
        assert (ROOT / "web" / s["image"]).is_file(), s["image"]
