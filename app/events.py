"""Build and validate social_cue (and caption) events."""

from __future__ import annotations

import json
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=4)
def _load_schema(name: str) -> dict:
    for path in (ROOT / "schemas" / name, ROOT / "reference" / name):
        if path.exists():
            return json.loads(path.read_text())
    raise FileNotFoundError(name)


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_load_schema(name), format_checker=FormatChecker())


def validate_social_cue(event: dict[str, Any]) -> None:
    _validator("social_cue.schema.json").validate(event)


def validate_event(event: dict[str, Any]) -> None:
    """Validate social_cue via extension schema; other types via Graption events schema."""
    if event.get("type") == "social_cue":
        validate_social_cue(event)
        return
    try:
        _validator("events.schema.json").validate(event)
    except FileNotFoundError:
        # Minimal caption check if Graption schema missing.
        required = {"type", "session_id", "schema_version"}
        if not required.issubset(event):
            raise ValidationError("missing envelope fields")


def make_social_cue(
    *,
    session_id: str,
    t: float,
    output: dict[str, Any],
    notified: bool,
    source: str,
    input_kind: str,
    model_version: str,
    speaker_id: str = "unknown",
    related_caption_id: str | None = None,
    cue_id: str | None = None,
) -> dict[str, Any]:
    cue = (output.get("cue") or "")[:80]
    event = {
        "type": "social_cue",
        "session_id": session_id,
        "schema_version": "1.2",
        "cue_id": cue_id or str(uuid.uuid4()),
        "t": float(t),
        "cue_type": output["cue_type"],
        "cue": cue,
        "visual_evidence": output.get("visual_evidence"),
        "audio_evidence": output.get("audio_evidence"),
        "suggested_response": output.get("suggested_response"),
        "confidence": float(output["confidence"]),
        "should_notify": bool(output["should_notify"]),
        "notified": bool(notified),
        "speaker_id": speaker_id,
        "related_caption_id": related_caption_id,
        "source": source,
        "input_kind": input_kind,
        "model_version": model_version,
    }
    validate_social_cue(event)
    return event


def make_caption(
    *,
    session_id: str,
    t_start: float,
    t_end: float,
    text: str,
    caption_id: str | None = None,
) -> dict[str, Any]:
    event = {
        "type": "caption",
        "session_id": session_id,
        "schema_version": "1.2",
        "caption_id": caption_id or str(uuid.uuid4()),
        "t_start": float(t_start),
        "t_end": float(t_end),
        "text": text,
        "speaker_id": "unknown",
        "model_versions": {"asr": "web-speech", "asd": "none"},
    }
    validate_event(event)
    return event
