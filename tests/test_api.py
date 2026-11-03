"""API tests with TestClient."""

from __future__ import annotations

import statistics
import time

import pytest
from fastapi.testclient import TestClient

from app import grok
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _without_xai_key(monkeypatch: pytest.MonkeyPatch):
    """Keep API tests deterministic even when a developer has a local key."""
    monkeypatch.delenv("XAI_API_KEY", raising=False)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["grok"] in {"configured", "missing_key"}
    assert "model" in body


def test_stt_missing_key_returns_503():
    response = client.post(
        "/api/stt",
        files={"file": ("sample.wav", b"RIFFdata", "audio/wav")},
    )
    assert response.status_code == 503


def test_stt_returns_transcript(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key-not-real")

    async def fake_transcribe(*_args, **_kwargs):
        return "hello from the microphone"

    monkeypatch.setattr(grok, "transcribe", fake_transcribe)
    response = client.post(
        "/api/stt",
        files={"file": ("sample.wav", b"RIFFdata", "audio/wav")},
    )
    assert response.status_code == 200
    assert response.json() == {"text": "hello from the microphone"}


def test_analyze_canned_wave_and_dedupe():
    sid = client.post("/api/sessions").json()["session_id"]
    r1 = client.post(
        "/api/analyze",
        json={
            "session_id": sid,
            "t": 61.0,
            "transcript_window": "",
            "scenario_id": "wave",
        },
    )
    assert r1.status_code == 200
    body = r1.json()
    assert body["source"] == "canned"
    assert body["event"]["type"] == "social_cue"
    assert body["event"]["notified"] is True
    assert body["hud"] is not None

    r2 = client.post(
        "/api/analyze",
        json={
            "session_id": sid,
            "t": 64.0,
            "transcript_window": "",
            "scenario_id": "wave",
        },
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["event"]["notified"] is False
    assert body2["hud"] is None


def test_recap_heuristic():
    r = client.post("/api/recap", json={"session_id": "sample"})
    assert r.status_code == 200
    body = r.json()
    assert body["source"] in {"heuristic", "grok"}
    assert "recap" in body
    assert "addressed_to_you" in body["recap"]


def test_analyze_latency_logged():
    sid = client.post("/api/sessions").json()["session_id"]
    samples: list[float] = []
    for i in range(5):
        t0 = time.perf_counter()
        r = client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "t": float(i),
                "transcript_window": "",
                "scenario_id": "dinner" if i == 0 else "sarcasm",
            },
        )
        assert r.status_code == 200
        samples.append((time.perf_counter() - t0) * 1000)
    samples_sorted = sorted(samples)
    p50 = statistics.median(samples_sorted)
    p95 = samples_sorted[max(0, int(len(samples_sorted) * 0.95) - 1)]
    print(f"analyze latency p50={p50:.1f}ms p95={p95:.1f}ms", flush=True)


def test_heuristic_recap_uses_speaker_names(tmp_path, monkeypatch):
    import app.main as m

    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "speakers.json").write_text('{"speakers": {"f1": {"name": "Sarah"}}}')
    monkeypatch.setattr(m, "ROOT", tmp_path)
    caps = [{"type": "caption", "speaker_id": "f1", "t_start": 1.0, "text": "Vaibhav, can you help?"},
            {"type": "caption", "speaker_id": "unknown", "t_start": 2.0, "text": "hi"},
            {"type": "caption", "speaker_id": "f9", "t_start": 3.0, "text": "hello"}]
    r = m.heuristic_recap(caps, "Vaibhav")
    assert r["addressed_to_you"][0]["speaker"] == "Sarah"
    assert [p["speaker"] for p in r["per_speaker"]] == ["Sarah", "Someone", "f9"]
