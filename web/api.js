/**
 * SocialLens API client. With ?mock=1, reads /contracts/fixtures instead of /api/*
 * and replays ws_stream.jsonl with _delay_ms delays.
 */
(function (global) {
  "use strict";

  const MOCK =
    typeof location !== "undefined" &&
    new URLSearchParams(location.search).get("mock") === "1";

  const API_BASE = (() => {
    if (MOCK) return "";
    if (typeof location === "undefined") return "http://localhost:8000";
    if (location.port === "8000") return "";
    return "http://localhost:8000";
  })();

  function fixtureUrl(name) {
    return `/contracts/fixtures/${name}`;
  }

  function errorMessage(body, fallback) {
    if (!body) return fallback;
    if (typeof body.error === "string") return body.error;
    const d = body.detail;
    if (typeof d === "string") return d;
    if (d && typeof d === "object" && typeof d.error === "string") return d.error;
    if (Array.isArray(d) && d[0] && d[0].msg) return d.map((x) => x.msg).join("; ");
    return fallback;
  }

  async function getJson(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) {
      let body = null;
      try {
        body = await res.json();
      } catch (_) {
        /* ignore */
      }
      const err = new Error(errorMessage(body, res.statusText || String(res.status)));
      err.status = res.status;
      err.body = body;
      throw err;
    }
    return res.json();
  }

  async function health() {
    if (MOCK) return getJson(fixtureUrl("health.json"));
    return getJson(`${API_BASE}/api/health`);
  }

  async function createSession() {
    if (MOCK) return getJson(fixtureUrl("session.json"));
    return getJson(`${API_BASE}/api/sessions`, { method: "POST" });
  }

  async function deleteSession(id) {
    if (MOCK) return { ok: true, session_id: id };
    const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!res.ok && res.status !== 204) {
      const err = new Error(res.statusText || String(res.status));
      err.status = res.status;
      throw err;
    }
    return { ok: true };
  }

  async function postCaption(id, caption) {
    if (MOCK) {
      return {
        type: "caption",
        session_id: id,
        schema_version: "1.2",
        caption_id: "mock-caption",
        t_start: caption.t_start,
        t_end: caption.t_end,
        text: caption.text,
        speaker_id: "unknown",
        model_versions: { asr: "web-speech", asd: "none" },
      };
    }
    return getJson(`${API_BASE}/api/sessions/${encodeURIComponent(id)}/captions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(caption),
    });
  }

  function pickAnalyzeFixture(req) {
    const sid = req && req.scenario_id;
    if (sid === "dinner") return "analyze_dinner.json";
    if (sid === "sarcasm") return "analyze_sarcasm.json";
    if (sid === "wave") return "analyze_wave.json";
    const text = ((req && req.transcript_window) || "").toLowerCase();
    if (text.includes("dinner")) return "analyze_dinner.json";
    if (text.includes("meeting") || text.includes("great")) return "analyze_sarcasm.json";
    if (!text.trim()) return "analyze_wave.json";
    return "analyze_none.json";
  }

  async function analyze(req) {
    if (MOCK) return getJson(fixtureUrl(pickAnalyzeFixture(req)));
    return getJson(`${API_BASE}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  }

  async function events(id) {
    if (MOCK) {
      const dinner = await getJson(fixtureUrl("analyze_dinner.json"));
      return { events: [dinner.event] };
    }
    return getJson(`${API_BASE}/api/sessions/${encodeURIComponent(id)}/events`);
  }

  async function recap(id) {
    if (MOCK) return getJson(fixtureUrl("recap.json"));
    return getJson(`${API_BASE}/api/recap`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: id }),
    });
  }

  async function stt(blob) {
    if (MOCK) return { text: "" };
    const fd = new FormData();
    const isWav = blob.type && blob.type.includes("wav");
    fd.append("file", blob, isWav ? "chunk.wav" : "chunk.webm");
    const res = await fetch(`${API_BASE}/api/stt`, { method: "POST", body: fd });
    if (!res.ok) {
      let body = null;
      try {
        body = await res.json();
      } catch (_) {
        /* ignore */
      }
      const err = new Error(errorMessage(body, res.statusText || String(res.status)));
      err.status = res.status;
      err.body = body;
      throw err;
    }
    return res.json();
  }

  /**
   * Open a session websocket. Returns a handle with .close().
   * In mock mode, replays contracts/fixtures/ws_stream.jsonl using _delay_ms.
   */
  function openWs(id, onMsg) {
    let closed = false;
    let timer = null;
    let socket = null;

    function close() {
      closed = true;
      if (timer != null) {
        clearTimeout(timer);
        timer = null;
      }
      if (socket) {
        try {
          socket.close();
        } catch (_) {
          /* ignore */
        }
        socket = null;
      }
    }

    if (MOCK) {
      (async () => {
        const res = await fetch(fixtureUrl("ws_stream.jsonl"));
        if (!res.ok) throw new Error(`mock ws_stream: ${res.status}`);
        const text = await res.text();
        const lines = text
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .map((l) => JSON.parse(l));

        let i = 0;
        function next() {
          if (closed || i >= lines.length) return;
          const raw = lines[i++];
          const delay = typeof raw._delay_ms === "number" ? raw._delay_ms : 1500;
          const { _delay_ms, ...msg } = raw;
          timer = setTimeout(() => {
            if (closed) return;
            if (typeof onMsg === "function") onMsg(msg);
            next();
          }, delay);
        }
        next();
      })().catch((err) => {
        console.error("[api.openWs mock]", err);
      });
      return { close, mock: true };
    }

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const host =
      API_BASE === ""
        ? location.host
        : API_BASE.replace(/^https?:\/\//, "");
    const url = `${proto}//${host}/ws/sessions/${encodeURIComponent(id)}`;
    socket = new WebSocket(url);
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (typeof onMsg === "function") onMsg(msg);
      } catch (err) {
        console.error("[api.openWs] bad message", err);
      }
    };
    socket.onerror = (err) => console.error("[api.openWs]", err);
    return { close, socket };
  }

  global.SocialLensApi = {
    MOCK,
    API_BASE,
    health,
    createSession,
    deleteSession,
    postCaption,
    analyze,
    events,
    recap,
    stt,
    openWs,
  };
})(typeof window !== "undefined" ? window : globalThis);
