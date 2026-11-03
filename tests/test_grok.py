"""Grok client unit tests (httpx mocked)."""

from __future__ import annotations

import asyncio
import json

import httpx

from app import grok


def test_analyze_frame_missing_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    async def run():
        try:
            await grok.analyze_frame(
                image_b64=None, transcript_window="hi", user_name="Vaibhav"
            )
            raise AssertionError("expected GrokUnavailable")
        except grok.GrokUnavailable:
            pass

    asyncio.run(run())


def test_analyze_frame_parses_output_text(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key-not-real")
    cue = {
        "cue_type": "question_to_you",
        "cue": "They asked you to dinner Friday",
        "visual_evidence": None,
        "audio_evidence": "dinner?",
        "suggested_response": "Sure",
        "confidence": 0.9,
        "should_notify": True,
    }
    payload = {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(cue)}],
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/responses" in str(request.url)
        assert request.headers.get("Authorization", "").startswith("Bearer ")
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)

    class FakeClient(httpx.AsyncClient):
        def __init__(self, *a, **k):
            super().__init__(*a, transport=transport, **k)

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)

    out = asyncio.run(
        grok.analyze_frame(
            image_b64="abc", transcript_window="[0:12] hi", user_name="Vaibhav"
        )
    )
    assert out["cue_type"] == "question_to_you"
    assert out["confidence"] == 0.9


def test_recap_parses_choices(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key-not-real")
    recap = {
        "overall_summary": "ok",
        "per_speaker": [],
        "addressed_to_you": [],
        "action_items": [],
        "tone_highlights": [],
        "disclaimer": "Tone highlights are model guesses about tone of voice, not feelings.",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/chat/completions" in str(request.url)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(recap)}}]}
        )

    transport = httpx.MockTransport(handler)

    class FakeClient(httpx.AsyncClient):
        def __init__(self, *a, **k):
            super().__init__(*a, transport=transport, **k)

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    out = asyncio.run(grok.recap("[0:11] Alex: Vaibhav, hi?", "Vaibhav"))
    assert out["overall_summary"] == "ok"
