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
    speechNetworkFails: 0,
    speechDisabled: false,
    lastToastAt: 0,
    mediaRecorder: null,
    micStream: null,
    sttBusy: false,
    sttLooping: false,
  };

  const textOnlyBtn = document.getElementById("textOnlyBtn");

  els.consentCheck.addEventListener("change", () => {
    const ok = els.consentCheck.checked;
    els.startBtn.disabled = !ok;
    if (textOnlyBtn) textOnlyBtn.disabled = !ok;
  });

  function resetSessionLocal() {
    state.stopped = false;
    state.speechDisabled = false;
    state.speechNetworkFails = 0;
    state.sessionId = null;
    state.startedAt = performance.now();
    state.finals = [];
    state.recentCues = [];
    state.seenCueIds = new Set();
    els.cueList.innerHTML = "";
    els.transcript.textContent = "";
    els.interim.textContent = "";
    els.toasts.innerHTML = "";
    renderHud(null);
  }

  els.startBtn.addEventListener("click", () => {
    resetSessionLocal();
    // Prefer xAI STT via MediaRecorder (works when Chrome→Google STT is blocked).
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

  function toast(msg, { force } = {}) {
    const now = Date.now();
    if (!force && now - state.lastToastAt < 2500) return; // prevent toast storms
    state.lastToastAt = now;
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
        const health = await api.health().catch(() => null);
        if (!api.MOCK && health && health.grok === "configured") {
          await startXaiStt();
        } else {
          startSpeech();
        }
        startFrameLoop();
        setTimeout(() => {
          if (!state.stopped && state.finals.length === 0) {
            els.chromeWarn.classList.add("visible");
            els.chromeWarn.textContent =
              "No transcript yet — keep speaking, or type below.";
            typeInput?.focus();
          }
        }, 8000);
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

  function stopXaiStt() {
    state.sttLooping = false;
    try {
      if (state.mediaRecorder && state.mediaRecorder.state !== "inactive") {
        state.mediaRecorder.ondataavailable = null;
        state.mediaRecorder.stop();
      }
    } catch (_) {
      /* ignore */
    }
    state.mediaRecorder = null;
    if (state.micStream) {
      state.micStream.getTracks().forEach((t) => t.stop());
      state.micStream = null;
    }
  }

  function encodeWav(audioBuffer) {
    const numChannels = 1;
    const sampleRate = audioBuffer.sampleRate;
    const source = audioBuffer.getChannelData(0);
    // Downmix if needed
    let samples = source;
    if (audioBuffer.numberOfChannels > 1) {
      const ch1 = audioBuffer.getChannelData(1);
      samples = new Float32Array(source.length);
      for (let i = 0; i < source.length; i++) samples[i] = (source[i] + ch1[i]) * 0.5;
    }
    // Resample to 16k for STT friendliness
    const targetRate = 16000;
    const ratio = sampleRate / targetRate;
    const newLen = Math.floor(samples.length / ratio);
    const resampled = new Float32Array(newLen);
    for (let i = 0; i < newLen; i++) resampled[i] = samples[Math.floor(i * ratio)] || 0;

    const dataLength = resampled.length * 2;
    const buffer = new ArrayBuffer(44 + dataLength);
    const view = new DataView(buffer);
    const writeStr = (off, str) => {
      for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
    };
    writeStr(0, "RIFF");
    view.setUint32(4, 36 + dataLength, true);
    writeStr(8, "WAVE");
    writeStr(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, targetRate, true);
    view.setUint32(28, targetRate * numChannels * 2, true);
    view.setUint16(32, numChannels * 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, "data");
    view.setUint32(40, dataLength, true);
    let offset = 44;
    for (let i = 0; i < resampled.length; i++) {
      const s = Math.max(-1, Math.min(1, resampled[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      offset += 2;
    }
    return new Blob([buffer], { type: "audio/wav" });
  }

  async function blobToWav(blob) {
    const ctx = new AudioContext();
    try {
      const arr = await blob.arrayBuffer();
      const audioBuf = await ctx.decodeAudioData(arr.slice(0));
      return encodeWav(audioBuf);
    } finally {
      await ctx.close().catch(() => {});
    }
  }

  function recordCompleteChunk(stream, mime, ms) {
    return new Promise((resolve, reject) => {
      const parts = [];
      let rec;
      try {
        rec = new MediaRecorder(stream, { mimeType: mime, audioBitsPerSecond: 64000 });
      } catch (err) {
        reject(err);
        return;
      }
      state.mediaRecorder = rec;
      rec.ondataavailable = (ev) => {
        if (ev.data && ev.data.size) parts.push(ev.data);
      };
      rec.onerror = (ev) => reject(ev.error || new Error("MediaRecorder error"));
      rec.onstop = () => {
        resolve(new Blob(parts, { type: mime }));
      };
      rec.start(); // complete file (no timeslice) — timeslice webm is invalid for STT
      setTimeout(() => {
        if (rec.state !== "inactive") {
          try {
            rec.stop();
          } catch (_) {
            resolve(new Blob(parts, { type: mime }));
          }
        }
      }, ms);
    });
  }

  async function startXaiStt() {
    if (!navigator.mediaDevices?.getUserMedia) {
      disableSpeech("No mic API — type below.");
      return;
    }
    try {
      const mic = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
        video: false,
      });
      state.micStream = mic;
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      if (!mime) {
        disableSpeech("MediaRecorder unsupported — type below.");
        return;
      }

      state.sttLooping = true;
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent =
        "Listening via xAI STT (WAV). Speak clearly; text every ~3s.";
      els.interim.textContent = "(listening via xAI)";
      console.log("[stt] loop starting", mime);

      // Fire-and-forget loop
      void (async () => {
        while (state.sttLooping && !state.stopped && state.micStream) {
          try {
            const raw = await recordCompleteChunk(state.micStream, mime, 3000);
            if (!state.sttLooping || state.stopped) break;
            if (!raw || raw.size < 500) continue;
            let wav;
            try {
              wav = await blobToWav(raw);
            } catch (decodeErr) {
              console.warn("[stt] decode failed, skipping chunk", decodeErr);
              continue;
            }
            await handleSttChunk(wav);
          } catch (err) {
            console.error("[stt] chunk loop", err);
            if (state.stopped || !state.sttLooping) break;
            await new Promise((r) => setTimeout(r, 500));
          }
        }
      })();
    } catch (err) {
      console.error("[stt] mic failed", err);
      disableSpeech("Mic permission denied for STT. Allow mic, or type below.");
    }
  }

  async function handleSttChunk(blob) {
    if (!state.sessionId || state.stopped) return;
    state.sttBusy = true;
    els.interim.textContent = "(transcribing…)";
    try {
      const res = await api.stt(blob);
      const text = (res && res.text ? String(res.text) : "").trim();
      if (!text) {
        els.interim.textContent = "(listening via xAI)";
        return;
      }
      injectCaption(text);
      els.interim.textContent = "(listening via xAI)";
    } catch (err) {
      console.error("[stt]", err);
      els.interim.textContent = "(STT error — type below works)";
      toast(`STT: ${(err && err.message) || err}`, { force: false });
    } finally {
      state.sttBusy = false;
    }
  }

  function stopCapture({ offerDiscard }) {
    state.stopped = true;
    stopFrameLoop();
    stopSpeech();
    stopXaiStt();
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

  function disableSpeech(reason) {
    state.speechDisabled = true;
    stopSpeech();
    els.chromeWarn.classList.add("visible");
    els.chromeWarn.textContent = reason;
    els.interim.textContent = "";
    toast(reason, { force: true });
    typeInput?.focus();
  }

  function startSpeech() {
    if (state.speechDisabled || state.stopped) return;

    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      disableSpeech("No SpeechRecognition in this browser. Type below (manual text works).");
      return;
    }
    stopSpeech();

    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      state.speechNetworkFails = 0;
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent = "Listening… (Chrome→Google STT). If this fails, type below.";
      els.interim.textContent = "(listening)";
    };

    rec.onresult = (ev) => {
      state.speechNetworkFails = 0;
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
      if (ev.error === "network" || ev.error === "service-not-allowed" || ev.error === "not-allowed") {
        state.speechNetworkFails += 1;
        // Chrome Web Speech calls Google's cloud STT. VPN/firewall/offline → network.
        // Stop restart loop after 1 failure so we don't spam toasts.
        disableSpeech(
          "Live mic STT blocked (Chrome→Google network error). Manual type box works — use that. Fix: disable VPN, allow Google, or chrome://settings/content/microphone"
        );
        return;
      }
      els.chromeWarn.classList.add("visible");
      els.chromeWarn.textContent = `Speech error: ${ev.error}. Type below.`;
    };

    rec.onend = () => {
      state.recognition = null;
      if (state.stopped || state.speechDisabled) return;
      setTimeout(() => {
        if (state.stopped || state.speechDisabled || state.recognition) return;
        try {
          startSpeech();
        } catch (_) {
          /* ignore */
        }
      }, 400);
    };

    state.recognition = rec;
    try {
      rec.start();
      console.log("[speech] started");
    } catch (err) {
      console.error("[speech] start failed", err);
      disableSpeech("Could not start speech recognition. Type below (manual text works).");
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
