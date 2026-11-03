"""SocialLens FastAPI app — Track A backend."""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import grok
from app.dedupe import decide_notified
from app.events import make_caption, make_social_cue
from app.prompts import DISCLAIMER
from app.store import store

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

USER_NAME = os.getenv("USER_NAME", "Vaibhav")

app = FastAPI(title="SocialLens")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- static mounts (mock mode + web) ---
for mount, rel in (("/contracts", "contracts"), ("/web", "web")):
    path = ROOT / rel
    path.mkdir(parents=True, exist_ok=True)
    app.mount(mount, StaticFiles(directory=str(path)), name=rel.strip("/"))


# ---------- helpers: canned + hud stubs ----------

def _load_fixture(name: str) -> dict[str, Any]:
    path = ROOT / "contracts" / "fixtures" / name
    if path.exists():
        return json.loads(path.read_text())
    raise FileNotFoundError(name)


def get_canned(scenario_id: str) -> dict[str, Any]:
    try:
        from app.canned import get as canned_get  # type: ignore

        return canned_get(scenario_id)
    except Exception:
        pass
    mapping = {
        "dinner": "analyze_dinner.json",
        "sarcasm": "analyze_sarcasm.json",
        "wave": "analyze_wave.json",
        "none": "analyze_none.json",
    }
    fname = mapping.get(scenario_id or "", "analyze_none.json")
    try:
        return _load_fixture(fname)
    except FileNotFoundError:
        return {
            "event": {
                "type": "social_cue",
                "session_id": "demo",
                "schema_version": "1.2",
                "cue_id": str(uuid.uuid4()),
                "t": 0.0,
                "cue_type": "none",
                "cue": "No cue",
                "visual_evidence": None,
                "audio_evidence": None,
                "suggested_response": None,
                "confidence": 0.8,
                "should_notify": False,
                "notified": False,
                "speaker_id": "unknown",
                "related_caption_id": None,
                "source": "canned",
                "input_kind": "demo_input",
                "model_version": "canned-v0",
            },
            "hud": None,
            "source": "canned",
            "latency_ms": 0,
        }


def hud_for(event: dict[str, Any]) -> dict[str, Any] | None:
    """Prefer Track C's app.cues.hud_for; stub only if import fails."""
    try:
        from app.cues import hud_for as cues_hud

        return cues_hud(event)
    except Exception:
        pass
    if not event.get("notified"):
        return None
    reply = event.get("suggested_response")
    text = event.get("cue") or ""
    icons = {
        "question_to_you": "questionmark.bubble",
        "sarcasm_or_joke": "face.smiling",
        "greeting_gesture": "hand.wave",
        "turn_taking": "arrow.triangle.2.circlepath",
        "other": "info.circle",
    }
    return {
        "kind": "social_cue",
        "text": text,
        "reply": reply,
        "icon": icons.get(event.get("cue_type", ""), "info.circle"),
        "color": "#4FC3F7",
        "priority": 3,
        "ttl_s": 8,
        "footnote": "model guess",
        "tree": {
            "kind": "FlexBox",
            "direction": "column",
            "children": [
                {"kind": "Text", "style": "heading", "text": text},
                *(
                    [{"kind": "Text", "style": "body", "text": f"Say: {reply}"}]
                    if reply
                    else []
                ),
                {
                    "kind": "Text",
                    "style": "meta",
                    "color": "secondary",
                    "text": "model guess",
                },
            ],
        },
    }


def _fmt_t(t: float) -> str:
    m = int(t // 60)
    s = int(t % 60)
    return f"{m}:{s:02d}"


def _speaker_names() -> dict[str, str]:
    """face_id -> display name from data/speakers.json (dashboard-only overlay; never sent to Grok)."""
    try:
        data = json.loads((ROOT / "data" / "speakers.json").read_text())
        return {k: v["name"] for k, v in data.get("speakers", {}).items() if v.get("name")}
    except (OSError, ValueError, AttributeError, KeyError, TypeError):
        return {}


def heuristic_recap(events: list[dict[str, Any]], user_name: str) -> dict[str, Any]:
    name_re = re.compile(rf"\b{re.escape(user_name)}\b", re.I)
    action_re = re.compile(
        r"can you|could you|we need|by (mon|tue|wed|thu|fri|sat|sun|monday|tuesday|wednesday|thursday|friday)",
        re.I,
    )
    captions = [e for e in events if e.get("type") == "caption"]
    per: dict[str, list[str]] = {}
    addressed: list[dict[str, str]] = []
    actions: list[dict[str, Any]] = []
    names = _speaker_names()
    for c in captions:
        spk = c.get("speaker_id") or "unknown"
        spk = "Someone" if spk == "unknown" else names.get(spk, spk)
        per.setdefault(spk, []).append(c.get("text") or "")
        text = c.get("text") or ""
        t = _fmt_t(float(c.get("t_start") or 0))
        if name_re.search(text):
            addressed.append(
                {
                    "t": t,
                    "speaker": spk,
                    "quote": text,
                    "what_they_need": "Response from you",
                }
            )
        if action_re.search(text):
            actions.append({"owner": user_name, "item": text[:80], "due": None})
    per_speaker = [
        {"speaker": k, "summary": f"{len(v)} lines. First: {v[0][:60]}" if v else "—"}
        for k, v in per.items()
    ]
    overall = (
        f"{len(captions)} captions across {len(per)} speakers."
        if captions
        else "No captions in this session."
    )
    return {
        "overall_summary": overall,
        "per_speaker": per_speaker,
        "addressed_to_you": addressed,
        "action_items": actions,
        "tone_highlights": [],
        "disclaimer": DISCLAIMER,
    }


def build_compact_log(events: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for e in events:
        t = e.get("type")
        if t == "caption":
            spk = e.get("speaker_id") or "Someone"
            if spk == "unknown":
                spk = "Someone"
            lines.append(f"[{_fmt_t(float(e.get('t_start') or 0))}] {spk}: {e.get('text')}")
        elif t == "sound_event":
            lines.append(
                f"[{_fmt_t(float(e.get('t') or 0))}] SOUND {e.get('label')} ({e.get('confidence')})"
            )
        elif t == "social_cue" and e.get("notified"):
            lines.append(
                f"[{_fmt_t(float(e.get('t') or 0))}] CUE {e.get('cue_type')}: \"{e.get('cue')}\""
            )
        elif t == "tone_result" and e.get("tag"):
            lines.append(
                f"[{_fmt_t(0)}] TONE {e.get('tag')} on caption {e.get('caption_id')}"
            )
    return "\n".join(lines)


def load_sample_events() -> list[dict[str, Any]]:
    for path in (
        ROOT / "data" / "sample_session.jsonl",
        ROOT / "reference" / "sample_session.jsonl",
    ):
        if path.exists():
            out: list[dict[str, Any]] = []
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                # Graption replay logs wrap as {_replay_t, event}
                if isinstance(obj, dict) and "event" in obj and "type" not in obj:
                    obj = obj["event"]
                out.append(obj)
            return out
    return []


# ---------- request models ----------


class CaptionIn(BaseModel):
    t_start: float
    t_end: float
    text: str


class AnalyzeIn(BaseModel):
    session_id: str
    t: float
    transcript_window: str = ""
    image_b64: str | None = None
    scenario_id: str | None = None
    input_kind: str | None = None


class RecapIn(BaseModel):
    session_id: str


# ---------- routes ----------


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "grok": "configured" if grok.configured() else "missing_key",
        "model": os.getenv("XAI_MODEL", "grok-4.20-0309-non-reasoning"),
    }


@app.post("/api/stt")
async def stt(file: UploadFile = File(...)) -> dict[str, str]:
    """Proxy short audio clips to xAI speech-to-text (server-side key only)."""
    if not grok.configured():
        raise HTTPException(status_code=503, detail={"error": "missing_key"})
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail={"error": "empty_file"})
    if len(raw) > 1_000_000:
        raise HTTPException(status_code=413, detail={"error": "audio_too_large"})
    try:
        text = await grok.transcribe(
            raw,
            filename=file.filename or "audio.webm",
            content_type=file.content_type or "audio/webm",
        )
    except grok.GrokUnavailable as exc:
        raise HTTPException(status_code=502, detail={"error": str(exc)}) from None
    return {"text": text}


@app.post("/api/sessions")
def create_session() -> dict[str, str]:
    sess = store.create("live")
    return {"session_id": sess.session_id}


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, bool]:
    ok = store.delete(session_id)
    return {"ok": ok}


@app.post("/api/sessions/{session_id}/captions")
async def post_caption(session_id: str, body: CaptionIn) -> dict[str, Any]:
    event = make_caption(
        session_id=session_id,
        t_start=body.t_start,
        t_end=body.t_end,
        text=body.text,
    )
    await store.append(session_id, event, None)
    return event


@app.post("/api/analyze")
async def analyze(body: AnalyzeIn) -> dict[str, Any]:
    t0 = time.perf_counter()
    sess = store.ensure(body.session_id)
    if sess.analyze_busy:
        return JSONResponse(status_code=429, content={"error": "busy"})
    if body.image_b64 and len(body.image_b64) > 1_400_000:  # ~1MB b64
        return JSONResponse(status_code=413, content={"error": "image_too_large"})
    sess.analyze_busy = True
    try:
        input_kind = body.input_kind or (
            "demo_input" if body.scenario_id else ("audio_only" if not body.image_b64 else "live_camera")
        )
        source = "canned"
        output: dict[str, Any] | None = None
        canned_hud: dict[str, Any] | None = None
        cue_id: str | None = None

        use_canned = body.scenario_id and not grok.configured()
        if use_canned:
            canned = get_canned(body.scenario_id or "none")
            ev = dict(canned["event"])
            output = {
                "cue_type": ev["cue_type"],
                "cue": ev["cue"],
                "visual_evidence": ev.get("visual_evidence"),
                "audio_evidence": ev.get("audio_evidence"),
                "suggested_response": ev.get("suggested_response"),
                "confidence": ev["confidence"],
                "should_notify": ev["should_notify"],
            }
            cue_id = ev.get("cue_id")
            canned_hud = canned.get("hud")
            source = "canned"
            model_version = "canned-v0"
        elif grok.configured():
            recent = [
                e["cue"]
                for e in sess.events
                if e.get("type") == "social_cue" and e.get("notified")
            ][-5:]
            try:
                output = await grok.analyze_frame(
                    image_b64=body.image_b64,
                    transcript_window=body.transcript_window,
                    user_name=USER_NAME,
                    recent_cues=recent,
                )
                source = "grok"
                model_version = os.getenv("XAI_MODEL", "grok-4.20-0309-non-reasoning")
            except grok.GrokUnavailable:
                if body.scenario_id:
                    canned = get_canned(body.scenario_id)
                    ev = canned["event"]
                    output = {
                        "cue_type": ev["cue_type"],
                        "cue": ev["cue"],
                        "visual_evidence": ev.get("visual_evidence"),
                        "audio_evidence": ev.get("audio_evidence"),
                        "suggested_response": ev.get("suggested_response"),
                        "confidence": ev["confidence"],
                        "should_notify": ev["should_notify"],
                    }
                    cue_id = ev.get("cue_id")
                    canned_hud = canned.get("hud")
                    source = "canned"
                    model_version = "canned-v0"
                else:
                    output = {
                        "cue_type": "none",
                        "cue": "No cue",
                        "visual_evidence": None,
                        "audio_evidence": None,
                        "suggested_response": None,
                        "confidence": 0.5,
                        "should_notify": False,
                    }
                    source = "canned"
                    model_version = "canned-v0"
        else:
            # live, no key
            if body.scenario_id:
                canned = get_canned(body.scenario_id)
                ev = canned["event"]
                output = {
                    "cue_type": ev["cue_type"],
                    "cue": ev["cue"],
                    "visual_evidence": ev.get("visual_evidence"),
                    "audio_evidence": ev.get("audio_evidence"),
                    "suggested_response": ev.get("suggested_response"),
                    "confidence": ev["confidence"],
                    "should_notify": ev["should_notify"],
                }
                cue_id = ev.get("cue_id")
                canned_hud = canned.get("hud")
            else:
                output = {
                    "cue_type": "none",
                    "cue": "Grok key not configured. Use Demo mode.",
                    "visual_evidence": None,
                    "audio_evidence": None,
                    "suggested_response": None,
                    "confidence": 1.0,
                    "should_notify": False,
                }
            source = "canned"
            model_version = "canned-v0"

        assert output is not None
        notified = decide_notified(
            should_notify=bool(output["should_notify"]),
            confidence=float(output["confidence"]),
            cue_type=output["cue_type"],
            cue=output.get("cue") or "",
            t=body.t,
            state=sess.dedupe,
        )
        event = make_social_cue(
            session_id=body.session_id,
            t=body.t,
            output=output,
            notified=notified,
            source=source,
            input_kind=input_kind,
            model_version=model_version,
            cue_id=cue_id,
        )
        if notified and canned_hud is not None and source == "canned":
            hud = canned_hud
        else:
            hud = hud_for(event)
        await store.append(body.session_id, event, hud)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        print(f"analyze_latency_ms={latency_ms}", flush=True)
        return {
            "event": event,
            "hud": hud,
            "source": source,
            "latency_ms": latency_ms,
        }
    finally:
        sess.analyze_busy = False


@app.get("/api/sessions/{session_id}/events")
def list_events(session_id: str) -> dict[str, Any]:
    if session_id == "sample":
        return {"events": load_sample_events()}
    sess = store.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail={"error": "not_found"})
    return {"events": sess.events}


@app.post("/api/recap")
async def recap(body: RecapIn) -> dict[str, Any]:
    if body.session_id == "sample":
        events = load_sample_events()
    else:
        sess = store.get(body.session_id)
        events = sess.events if sess else []

    if grok.configured():
        try:
            result = await grok.recap(build_compact_log(events), USER_NAME)
            return {"source": "grok", "recap": result, "message": None}
        except grok.GrokUnavailable as exc:
            return {
                "source": "heuristic",
                "message": f"Grok recap failed ({exc}); showing a rule-based summary.",
                "recap": heuristic_recap(events, USER_NAME),
            }

    return {
        "source": "heuristic",
        "message": "No XAI_API_KEY set; showing a rule-based summary, not Grok.",
        "recap": heuristic_recap(events, USER_NAME),
    }


@app.websocket("/ws/sessions/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    replay = websocket.query_params.get("replay") == "1"
    try:
        speed = float(websocket.query_params.get("speed") or "1")
    except ValueError:
        speed = 1.0
    speed = max(speed, 0.1)

    if replay:
        events = (
            load_sample_events()
            if session_id == "sample"
            else (store.get(session_id).events if store.get(session_id) else [])
        )
        # Prefer ws_stream fixture when available for demo session
        stream_path = ROOT / "contracts" / "fixtures" / "ws_stream.jsonl"
        if session_id in {"sample", "demo"} and stream_path.exists():
            prev = 0.0
            for line in stream_path.read_text().splitlines():
                if not line.strip():
                    continue
                msg = json.loads(line)
                delay = float(msg.pop("_delay_ms", 0)) / 1000.0 / speed
                if delay > 0:
                    await asyncio.sleep(delay)
                await websocket.send_json(msg)
            try:
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                return
        # time-based replay of stored events
        last_t = 0.0
        for ev in events:
            t = float(ev.get("t") or ev.get("t_start") or last_t)
            wait = max(0.0, (t - last_t) / speed)
            if wait:
                await asyncio.sleep(wait)
            last_t = t
            await websocket.send_json({"event": ev, "hud": hud_for(ev)})
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            return

    q = store.subscribe(session_id)
    try:
        while True:
            get_task = asyncio.create_task(q.get())
            recv_task = asyncio.create_task(websocket.receive_text())
            done, pending = await asyncio.wait(
                {get_task, recv_task}, return_when=asyncio.FIRST_COMPLETED
            )
            for p in pending:
                p.cancel()
            if recv_task in done:
                try:
                    recv_task.result()
                except WebSocketDisconnect:
                    break
            if get_task in done:
                msg = get_task.result()
                await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass
    finally:
        store.unsubscribe(session_id, q)
