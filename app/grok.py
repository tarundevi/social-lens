"""xAI Grok client. All xAI calls live only here."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from app.prompts import (
    RECAP_SCHEMA,
    RECAP_SYSTEM_PROMPT,
    SOCIAL_CUE_SCHEMA,
    SOCIALLENS_SYSTEM_PROMPT,
)


class GrokUnavailable(Exception):
    """Raised when XAI_API_KEY is missing or the API call fails."""


def _key() -> str | None:
    key = os.getenv("XAI_API_KEY", "").strip()
    return key or None


def _base() -> str:
    return os.getenv("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")


def _model() -> str:
    return os.getenv("XAI_MODEL", "grok-4.7")


def configured() -> bool:
    return _key() is not None


def _parse_responses_text(data: dict[str, Any]) -> str:
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if part.get("type") == "output_text" and "text" in part:
                return part["text"]
    raise GrokUnavailable("no output_text in responses payload")


async def analyze_frame(
    *,
    image_b64: str | None,
    transcript_window: str,
    user_name: str,
    recent_cues: list[str] | None = None,
) -> dict[str, Any]:
    """POST /responses with optional image + transcript; returns SocialCueOutput."""
    key = _key()
    if not key:
        raise GrokUnavailable("missing_key")

    recent = recent_cues or []
    user_text = (
        f"User name: {user_name}\n"
        f"Recent cues already shown (do not repeat): {json.dumps(recent)}\n"
        f"Transcript (last 30s, oldest first):\n{transcript_window or '(empty)'}"
    )
    content: list[dict[str, Any]] = []
    if image_b64:
        content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/jpeg;base64,{image_b64}",
            }
        )
    content.append({"type": "input_text", "text": user_text})

    body: dict[str, Any] = {
        "model": _model(),
        "input": [
            {"role": "system", "content": SOCIALLENS_SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "social_cue",
                "strict": True,
                "schema": SOCIAL_CUE_SCHEMA,
            }
        },
    }

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{_base()}/responses", headers=headers, json=body)
            if r.status_code >= 400:
                # Drop unverified params on retry is N/A here; surface as unavailable.
                raise GrokUnavailable(f"http {r.status_code}")
            text = _parse_responses_text(r.json())
            cue = json.loads(text)
            if isinstance(cue.get("cue"), str):
                cue["cue"] = cue["cue"][:80]
            return cue
    except GrokUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 — map all transport/parse errors
        raise GrokUnavailable(str(type(exc).__name__)) from None


async def transcribe(file_bytes: bytes, filename: str = "audio.webm", content_type: str = "audio/webm") -> str:
    """POST multipart to xAI /stt. Returns transcript text."""
    key = _key()
    if not key:
        raise GrokUnavailable("missing_key")
    model = os.getenv("XAI_STT_MODEL", "grok-voice-transcribe-2.0")
    headers = {"Authorization": f"Bearer {key}"}
    files = {"file": (filename, file_bytes, content_type)}
    data = {"model": model, "language": "en"}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{_base()}/stt", headers=headers, data=data, files=files)
            if r.status_code >= 400:
                raise GrokUnavailable(f"stt http {r.status_code}: {r.text[:200]}")
            payload = r.json()
            text = payload.get("text")
            if not isinstance(text, str):
                raise GrokUnavailable("stt missing text")
            return text.strip()
    except GrokUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GrokUnavailable(str(type(exc).__name__)) from None


async def recap(compact_log: str, user_name: str) -> dict[str, Any]:
    """POST chat/completions with RecapOutput json_schema."""
    key = _key()
    if not key:
        raise GrokUnavailable("missing_key")

    body = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": RECAP_SYSTEM_PROMPT},
            {"role": "user", "content": f"User: {user_name}\n{compact_log}"},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "recap", "schema": RECAP_SCHEMA, "strict": True},
        },
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{_base()}/chat/completions", headers=headers, json=body
            )
            if r.status_code >= 400:
                raise GrokUnavailable(f"http {r.status_code}")
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    except GrokUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GrokUnavailable(str(type(exc).__name__)) from None
