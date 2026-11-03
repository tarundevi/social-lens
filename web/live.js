/**
 * SocialLens live capture UI (Computer 2 / Track B).
 * Owns session lifecycle, getUserMedia, Web Speech, 3s analyze loop.
 */
(function () {
  "use strict";

  const api = window.SocialLensApi;
  if (!api) {
    console.error("SocialLensApi missing — load api.js first");
    return;
  }

  const els = {
    consent: document.getElementById("consent"),
    consentCheck: document.getElementById("consentCheck"),
    startBtn: document.getElementById("startBtn"),
    app: document.getElementById("app"),
    preview: document.getElementById("preview"),
    canvas: document.getElementById("frameCanvas"),
    badge: document.getElementById("captureBadge"),
    stopBtn: document.getElementById("stopBtn"),
    discardBtn: document.getElementById("discardBtn"),
    transcript: document.getElementById("transcript"),
    interim: document.getElementById("interim"),
    chromeWarn: document.getElementById("chromeWarn"),
    cueList: document.getElementById("cueList"),
    hudBox: document.getElementById("hudBox"),
    latency: document.getElementById("latency"),
    banner: document.getElementById("banner"),
    toasts: document.getElementById("toasts"),
  };

  const state = {
    sessionId: null,
    stream: null,
    ws: null,
    recognition: null,
    startedAt: 0,
    finals: [], // { t, text }
    analyzing: false,
    frameTimer: null,
    recentCues: [],
    seenCueIds: new Set(),
    stopped: false,
  };

  const textOnlyBtn = document.getElementById("textOnlyBtn");

  els.consentCheck.addEventListener("change", () => {
    const ok = els.consentCheck.checked;
    els.startBtn.disabled = !ok;
    if (textOnlyBtn) textOnlyBtn.disabled = !ok;
  });

  function resetSessionLocal() {
    state.stopped = false;
    state.sessionId = null;
    state.startedAt = performance.now();
    state.finals = [];
    state.recentCues = [];
    state.seenCueIds = new Set();
    els.cueList.innerHTML = "";
    els.transcript.textContent = "";
    els.interim.textContent = "";
    renderHud(null);
  }

  // SpeechRecognition.start() MUST run inside the click stack (before any await).
  els.startBtn.addEventListener("click", () => {
    resetSessionLocal();
    startSpeech(); // sync — keeps user-gesture / mic permission
    startSession({ camera: true }).catch(onFatal);
  });
  if (textOnlyBtn) {
    textOnlyBtn.addEventListener("click", () => {
      resetSessionLocal();
      startSession({ camera: false }).catch(onFatal);
    });
  }
  els.stopBtn.addEventListener("click", () => stopCapture({ offerDiscard: true }));
  els.discardBtn.addEventListener("click", () => discardSession().catch(onFatal));

  const typeForm = document.getElementById("typeForm");
  const typeInput = document.getElementById("typeInput");
  if (typeForm && typeInput) {
    typeForm.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const text = typeInput.value.trim();
      if (!text || !state.sessionId || state.stopped) {
        toast("Start a live session first, then type a line.");
        return;
      }
      injectCaption(text);
      typeInput.value = "";
    });
  }

  function injectCaption(text) {
    const t = (performance.now() - state.startedAt) / 1000;
    state.finals.push({ t, text });
    renderTranscript();
    els.interim.textContent = "";
    api
      .postCaption(state.sessionId, {
        t_start: Math.max(0, t - 2),
        t_end: t,
        text,
      })
      .catch(onFatal);
    // Kick analyze immediately so you don't wait for the 3s loop
    tickAnalyze().catch(onFatal);
  }

  api
    .health()
    .then((h) => {
      console.log("[SocialLens health]", h);
      if (api.MOCK) return;
      if (h && h.grok === "configured") {
        els.banner.textContent = `Live · Grok ready (${h.model || "grok"})`;
        els.banner.style.background = "#1b3a2f";
        els.banner.style.color = "#a5d6a7";
        els.banner.classList.add("visible");
      } else if (h && h.grok === "missing_key") {
        els.banner.textContent =
          "Backend is up but XAI_API_KEY is missing — cues will be canned until the key is set in .env.";
        els.banner.classList.add("visible");
      }
    })
    .catch((err) => {
      console.error("[SocialLens health]", err);
      if (api.MOCK) {
        toast("Could not load mock fixtures. Serve repo root or use http://localhost:8000/web/live.html");
        return;
      }
      toast("Backend not reachable. Start: uvicorn app.main:app --port 8000 — then open http://localhost:8000/web/live.html");
    });

  function toast(msg) {
    const el = document.createElement("div");
    el.className = "toast";
    el.textContent = msg;
    els.toasts.appendChild(el);
    setTimeout(() => el.remove(), 4500);
  }

  function onFatal(err) {
    console.error(err);
    if (err && err.status === 429) return; // busy: silent
    toast((err && err.message) || String(err));
  }

  function formatMs(ms) {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `[${m}:${String(r).padStart(2, "0")}]`;
  }

  function rollingTranscript() {
    const now = (performance.now() - state.startedAt) / 1000;
    const kept = state.finals.filter((f) => now - f.t <= 30);
    state.finals = kept;
    return kept.map((f) => `${formatMs(f.t * 1000)} Someone: ${f.text}`).join("\n");
  }

  function renderTranscript() {
    els.transcript.textContent = rollingTranscript();
  }

  function renderHud(hud) {
    els.hudBox.innerHTML = "";
    if (!hud) {
      els.hudBox.textContent = "—";
      return;
    }
    if (typeof window.renderHud === "function") {
      window.renderHud(els.hudBox, hud);
      return;
    }
    const text = document.createElement("div");
    text.textContent = hud.text || "";
    els.hudBox.appendChild(text);
    if (hud.reply) {
      const reply = document.createElement("div");
      reply.style.marginTop = "0.35rem";
      reply.style.color = "#8b9bb4";
      reply.textContent = `Say: ${hud.reply}`;
      els.hudBox.appendChild(reply);
    }
  }

  function pushCue(event, hud, latencyMs, source) {
    if (latencyMs != null) {
      els.latency.textContent = `last analyze ${latencyMs} ms${source ? ` · ${source}` : ""}`;
    }
    if (!event) return;
    // Still show HUD/latency for non-notify results so live mode doesn't look "stuck"
    if (event.cue_type === "none" || event.notified === false) {
      if (hud) renderHud(hud);
      else if (latencyMs != null) {
        els.hudBox.textContent = "No notify-worthy cue this tick (speak a clear question / wave).";
      }
      return;
    }
    const id = event.cue_id || `${event.t}-${event.cue}`;
    if (state.seenCueIds.has(id)) {
      if (hud) renderHud(hud);
      return;
    }
    state.seenCueIds.add(id);

    const li = document.createElement("li");
    const title = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = event.cue || event.cue_type || "";
    title.appendChild(strong);
    const meta = document.createElement("div");
    meta.className = "meta";
    const src = source || event.source || "";
    let metaText = `${event.cue_type || ""} · conf ${(event.confidence ?? 0).toFixed(2)}`;
    if (src) metaText += ` · ${src}`;
    if (event.suggested_response) metaText += ` · reply: ${event.suggested_response}`;
    meta.textContent = metaText;
    li.appendChild(title);
    li.appendChild(meta);
    els.cueList.prepend(li);
    while (els.cueList.children.length > 12) els.cueList.lastChild.remove();

    if (event.cue) {
      state.recentCues.unshift(event.cue);
      state.recentCues = state.recentCues.slice(0, 5);
    }
    renderHud(hud);
  }

  async function startSession({ camera } = { camera: true }) {
    // NOTE: startSpeech() is invoked from the click handler BEFORE this await chain.
    let sess = null;
    try {
      // Create session first so captions have an id as soon as speech finals arrive.
      sess = await api.createSession();
      state.sessionId = sess.session_id;

      if (camera) {
        if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
          toast("Camera needs http://localhost:8000/web/live.html — or use Text-only test");
          return;
        }
        // Video only. Audio MediaStream blocks webkitSpeechRecognition on Chrome.
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user" },
          audio: false,
        });
        state.stream = stream;
        els.preview.srcObject = stream;
        els.badge.classList.add("visible");
        els.badge.textContent = "● Camera on — speak OR type below";
      } else {
        els.badge.classList.remove("visible");
        els.preview.srcObject = null;
      }

      const hudLink = document.getElementById("hudLink");
      if (hudLink) {
        hudLink.href = `hud.html?session=${encodeURIComponent(state.sessionId)}`;
      }
      const recapLink = document.querySelector('nav a[href^="recap.html"]');
      if (recapLink) {
        recapLink.href = `recap.html?session=${encodeURIComponent(state.sessionId)}`;
      }

      els.consent.classList.add("hidden");
      els.app.classList.add("active");
      els.discardBtn.classList.add("hidden");

      state.ws = api.openWs(state.sessionId, (msg) => {
        if (msg && msg.event && msg.event.type === "social_cue") {
          pushCue(msg.event, msg.hud, null, msg.event.source);
        }
      });

      if (camera) {
        // Restart speech now that session exists (in case the primed one died).
        if (!state.recognition) startSpeech();
        startFrameLoop();
        setTimeout(() => {
          if (!state.stopped && state.finals.length === 0) {
            els.chromeWarn.classList.add("visible");
            els.chromeWarn.textContent =
              "Still no speech text. Use the box below — waiting will not help.";
            toast("Type a line and press Enter to see transcript + cues.");
            typeInput?.focus();
          }
        }, 3000);
      } else {
        els.chromeWarn.classList.add("visible");
        els.chromeWarn.textContent =
          "Text-only mode: type below and press Enter. Text must appear in Transcript.";
        toast("Type: Vaibhav, want to come to dinner Friday?");
        setTimeout(() => typeInput?.focus(), 50);
      }
    } catch (err) {
      stopSpeech();
      stopTracks();
      if (sess && sess.session_id) {
        try {
          await api.deleteSession(sess.session_id);
        } catch (_) {
          /* ignore */
        }
      }
      state.sessionId = null;
      throw err;
    }
  }

  function trackLive() {
    const stream = state.stream;
    if (!stream) return false;
    return stream.getTracks().some((t) => t.readyState === "live");
  }

  function stopTracks() {
    if (state.stream) {
      state.stream.getTracks().forEach((t) => t.stop());
      state.stream = null;
    }
    els.preview.srcObject = null;
    els.badge.classList.remove("visible");
  }

  function stopSpeech() {
    if (state.recognition) {
      try {
        state.recognition.onend = null;
        state.recognition.stop();
      } catch (_) {
        /* ignore */
      }
      state.recognition = null;
    }
  }

  function stopFrameLoop() {
    if (state.frameTimer != null) {
      clearInterval(state.frameTimer);
      state.frameTimer = null;
    }
  }

  function stopCapture({ offerDiscard }) {
    state.stopped = true;
    stopFrameLoop();
    stopSpeech();
    if (state.ws) {
      state.ws.close();
      state.ws = null;
    }
    stopTracks();
    if (offerDiscard) {
      els.discardBtn.classList.remove("hidden");
      toast("Capture stopped. Discard session to wipe server state, or refresh to start over.");
    }
  }

  async function discardSession() {
    stopCapture({ offerDiscard: false });
    if (state.sessionId) {
      try {
        await api.deleteSession(state.sessionId);
      } catch (err) {
        onFatal(err);
      }
    }
    state.sessionId = null;
    els.discardBtn.classList.add("hidden");
    els.app.classList.remove("active");
    els.consent.classList.remove("hidden");
    els.consentCheck.checked = false;
    els.startBtn.disabled = true;
    els.transcript.textContent = "";
    els.interim.textContent = "";
  }

  function startSpeech() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent =
        "This browser has no SpeechRecognition. Use Google Chrome, or type below.";
      return;
    }
    // Tear down any prior instance
    stopSpeech();

    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent = "Listening… speak clearly, or type below if nothing appears.";
      els.interim.textContent = "(listening)";
    };

    rec.onresult = (ev) => {
      let interim = "";
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const r = ev.results[i];
        const text = (r[0] && r[0].transcript ? r[0].transcript : "").trim();
        if (!text) continue;
        if (r.isFinal) {
          const t = state.startedAt
            ? (performance.now() - state.startedAt) / 1000
            : 0;
          state.finals.push({ t, text });
          renderTranscript();
          console.log("[speech final]", text);
          if (state.sessionId) {
            api
              .postCaption(state.sessionId, {
                t_start: Math.max(0, t - 2),
                t_end: t,
                text,
              })
              .catch(onFatal);
            tickAnalyze().catch(onFatal);
          }
        } else {
          interim += text + " ";
        }
      }
      els.interim.textContent = interim.trim() || "(listening)";
    };

    rec.onerror = (ev) => {
      console.warn("[speech error]", ev.error);
      if (ev.error === "aborted") return;
      if (ev.error === "no-speech") {
        els.interim.textContent = "(no speech heard — keep talking or type below)";
        return;
      }
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent = `Speech error: ${ev.error}. Type a line below to continue.`;
      toast(`Speech error: ${ev.error}`);
    };

    rec.onend = () => {
      state.recognition = null;
      if (state.stopped) return;
      // Restart even without camera tracks (speech should keep running).
      setTimeout(() => {
        if (state.stopped || state.recognition) return;
        try {
          startSpeech();
        } catch (_) {
          /* ignore */
        }
      }, 250);
    };

    state.recognition = rec;
    try {
      rec.start();
      console.log("[speech] started");
    } catch (err) {
      console.error("[speech] start failed", err);
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent = "Could not start speech. Type below instead.";
      toast("Could not start speech recognition — use the type box.");
    }
  }

  function grabJpegB64() {
    const video = els.preview;
    if (!video.videoWidth) return null;
    const maxW = 640;
    const scale = Math.min(1, maxW / video.videoWidth);
    const w = Math.round(video.videoWidth * scale);
    const h = Math.round(video.videoHeight * scale);
    const canvas = els.canvas;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
    const comma = dataUrl.indexOf(",");
    return comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl;
  }

  function startFrameLoop() {
    stopFrameLoop();
    const kick = () => tickAnalyze().catch(onFatal);
    const onReady = () => {
      els.preview.removeEventListener("loadeddata", onReady);
      kick();
    };
    if (els.preview.videoWidth) kick();
    else els.preview.addEventListener("loadeddata", onReady);
    state.frameTimer = setInterval(kick, 3000);
  }

  async function tickAnalyze() {
    if (state.stopped || state.analyzing || !state.sessionId) return;
    const hasCamera = trackLive();
    const transcript_window = rollingTranscript();
    // Text-only sessions analyze on transcript; camera sessions need a frame.
    if (!hasCamera && !transcript_window.trim() && !api.MOCK) return;

    const image_b64 = hasCamera ? grabJpegB64() : null;
    if (hasCamera && !image_b64 && !api.MOCK) return;
    const t = (performance.now() - state.startedAt) / 1000;

    state.analyzing = true;
    try {
      const res = await api.analyze({
        session_id: state.sessionId,
        t,
        transcript_window,
        image_b64: image_b64 || null,
        input_kind: "live_camera",
      });
      // Prefer WS for list items; HTTP updates latency + fills if WS missed it.
      pushCue(res.event, res.hud, res.latency_ms, res.source || (res.event && res.event.source));
    } catch (err) {
      if (err && err.status === 429) return;
      throw err;
    } finally {
      state.analyzing = false;
    }
  }
})();
