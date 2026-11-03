// Track D: Demo mode. Three scripted scenarios that work with no API key and no network.
//
//   import { mountDemo } from "/web/demo.js";
//   const demo = mountDemo(el, api, { sessionId });   // api = web/api.js (needs health() + analyze())
//   el.addEventListener("demo:result", (e) => renderHud(hudEl, e.detail.hud));
//
// Each button shows its DEMO INPUT image, types out the scripted transcript, then calls
// api.analyze({session_id, t, transcript_window, scenario_id, input_kind: "demo_input",
//              image_b64 (only when health.grok == "configured")}).
// Canned responses are labeled "Canned example (no API key)".

// Same content as contracts/scenarios.json; used if that file can't be fetched.
export const SCENARIOS = [
  { id: "dinner", title: "Dinner invite", image: "demo/dinner.jpg", t: 15.0,
    transcript: ["[0:10] Someone: hey", "[0:12] Someone: Vaibhav, want to come to dinner Friday?"] },
  { id: "sarcasm", title: "Sarcasm", image: "demo/sarcasm.jpg", t: 42.5,
    transcript: ["[0:40] Someone: Oh great, another three-hour meeting."] },
  { id: "wave", title: "Wave greeting", image: "demo/wave.jpg", t: 61.0, transcript: [] },
];

export const CANNED_LABEL = "Canned example (no API key)";
const TYPE_MS = 18;
const WEB_BASE = new URL("./", import.meta.url); // .../web/

const CSS = `
.sl-demo{font:15px/1.4 system-ui,sans-serif;color:inherit}
.sl-demo-buttons{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.sl-demo-buttons button{padding:8px 14px;border-radius:8px;border:1px solid #888;background:#263238;color:#fff;cursor:pointer}
.sl-demo-buttons button[disabled]{opacity:.5;cursor:wait}
.sl-demo-stage{position:relative;max-width:640px}
.sl-demo-stage img{width:100%;display:block;border-radius:8px}
.sl-demo-mark{position:absolute;right:8px;bottom:52px;padding:2px 8px;border-radius:4px;background:#b71c1c;color:#fff;font-weight:700;letter-spacing:.05em}
.sl-demo-transcript{font-family:ui-monospace,monospace;white-space:pre-wrap;min-height:3em;margin:8px 0;padding:8px;border-radius:6px;background:rgba(127,127,127,.12)}
.sl-demo-result{padding:8px 0}
.sl-demo-cue{font-weight:700;font-size:18px}
.sl-demo-tag{display:inline-block;margin-left:6px;padding:1px 8px;border-radius:10px;font-size:12px;background:#ffd54f;color:#000}
.sl-demo-tag.grok{background:#4fc3f7}
.sl-demo-meta{opacity:.75;font-size:13px}
.sl-demo-error{color:#e57373}
`;

function injectCss() {
  if (document.getElementById("sl-demo-css")) return;
  const style = document.createElement("style");
  style.id = "sl-demo-css";
  style.textContent = CSS;
  document.head.appendChild(style);
}

function h(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((c) => c != null));
  return node;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function loadScenarios() {
  try {
    const r = await fetch(new URL("../contracts/scenarios.json", WEB_BASE));
    if (r.ok) {
      const rows = await r.json();
      if (Array.isArray(rows) && rows.length) {
        return rows.map((row) => ({ ...SCENARIOS.find((s) => s.id === row.id), ...row }));
      }
    }
  } catch { /* offline or not served: use the inline copy */ }
  return SCENARIOS;
}

async function grokConfigured(api) {
  try {
    const health = await api.health();
    return health?.grok === "configured";
  } catch {
    return false;
  }
}

/** JPEG at url -> base64 without the data: prefix (API_SPEC.md image_b64). */
export async function imageToB64(url) {
  const blob = await (await fetch(url)).blob();
  const dataUrl = await new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result);
    fr.onerror = () => reject(fr.error);
    fr.readAsDataURL(blob);
  });
  return String(dataUrl).split(",", 2)[1];
}

async function typeOut(el, lines, isCancelled) {
  el.textContent = "";
  if (!lines.length) {
    el.textContent = "(no speech: visual cue only)";
    return;
  }
  for (const [i, line] of lines.entries()) {
    if (i) el.textContent += "\n";
    for (const ch of line) {
      if (isCancelled()) return;
      el.textContent += ch;
      await sleep(TYPE_MS);
    }
  }
}

function isBusy(err) {
  return err?.status === 429 || /\b429\b|busy/i.test(String(err?.message ?? err));
}

function renderResult(el, res) {
  const ev = res?.event ?? {};
  const canned = (res?.source ?? ev.source) === "canned";
  const tag = h("span", { className: `sl-demo-tag${canned ? "" : " grok"}`,
    textContent: canned ? CANNED_LABEL : "Grok (model guess)" });
  const reply = ev.suggested_response ? h("div", { textContent: `Say: ${ev.suggested_response}` }) : null;
  const conf = typeof ev.confidence === "number" ? ` · confidence ${ev.confidence.toFixed(2)}` : "";
  const lat = typeof res?.latency_ms === "number" ? ` · ${res.latency_ms} ms` : "";
  const shown = ev.notified === false ? " · not shown on HUD (low confidence or duplicate)" : "";
  el.replaceChildren(
    h("div", { className: "sl-demo-cue" }, ev.cue ?? "(no cue)", tag),
    reply,
    h("div", { className: "sl-demo-meta", textContent: `${ev.cue_type ?? "?"}${conf}${lat}${shown}` }),
  );
}

/**
 * Mount the demo-mode panel into el. Returns { destroy, run(id) }.
 * opts.sessionId: string or () => string|Promise<string>. Defaults to api.createSession() once, else "demo".
 * Fires "demo:result" (detail = AnalyzeResponse) and "demo:error" (detail = Error) on el.
 */
export function mountDemo(el, api, opts = {}) {
  injectCss();
  let token = 0;
  let sessionPromise = null;
  const buttons = h("div", { className: "sl-demo-buttons" });
  const img = h("img", { alt: "DEMO INPUT scenario image (drawn placeholder, not a photo)" });
  const stage = h("div", { className: "sl-demo-stage", hidden: true }, img,
    h("span", { className: "sl-demo-mark", textContent: "DEMO INPUT" }));
  const transcript = h("div", { className: "sl-demo-transcript", hidden: true });
  const result = h("div", { className: "sl-demo-result", "aria-live": "polite" });
  const root = h("div", { className: "sl-demo" }, buttons, stage, transcript, result);
  el.replaceChildren(root);

  const configuredP = grokConfigured(api);
  const scenariosP = loadScenarios();

  function sessionId() {
    if (typeof opts.sessionId === "function") return Promise.resolve(opts.sessionId());
    if (opts.sessionId) return Promise.resolve(opts.sessionId);
    sessionPromise ??= Promise.resolve(api.createSession?.())
      .then((s) => s?.session_id ?? "demo")
      .catch(() => "demo");
    return sessionPromise;
  }

  function setBusy(busy) {
    for (const b of buttons.querySelectorAll("button")) b.disabled = busy;
  }

  async function run(id) {
    const scenarios = await scenariosP;
    const s = scenarios.find((x) => x.id === id);
    if (!s) throw new Error(`unknown scenario ${id}`);
    const mine = ++token;
    const cancelled = () => mine !== token;
    setBusy(true);
    result.replaceChildren();
    const imgUrl = new URL(s.image, WEB_BASE).href;
    img.src = imgUrl;
    stage.hidden = false;
    transcript.hidden = false;
    try {
      await typeOut(transcript, s.transcript ?? [], cancelled);
      if (cancelled()) return;
      result.replaceChildren(h("div", { className: "sl-demo-meta", textContent: "Asking…" }));
      const req = {
        session_id: await sessionId(),
        t: s.t ?? 0,
        transcript_window: (s.transcript ?? []).join("\n"),
        scenario_id: s.id,
        input_kind: "demo_input",
      };
      if (await configuredP) req.image_b64 = await imageToB64(imgUrl);
      const res = await api.analyze(req);
      if (cancelled()) return;
      renderResult(result, res);
      el.dispatchEvent(new CustomEvent("demo:result", { detail: res }));
    } catch (err) {
      if (cancelled() || isBusy(err)) return;
      result.replaceChildren(h("div", { className: "sl-demo-error",
        textContent: `Demo request failed: ${err?.message ?? err}` }));
      el.dispatchEvent(new CustomEvent("demo:error", { detail: err }));
    } finally {
      if (!cancelled()) setBusy(false);
    }
  }

  scenariosP.then((scenarios) => {
    for (const s of scenarios) {
      const b = h("button", { type: "button", textContent: s.title });
      b.dataset.scenario = s.id;
      b.addEventListener("click", () => run(s.id));
      buttons.append(b);
    }
  });

  return {
    run,
    destroy() {
      token++;
      root.remove();
    },
  };
}
