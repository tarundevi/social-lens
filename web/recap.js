/* Recap timeline: speaker lanes, a tone-over-time chart, sound/social_cue markers,
 * and a replay button. Works against a loaded event list (mock jsonl or
 * GET /api/sessions/:id/events) plus a speakers.json map. */

const TONE_COLOR = {
  anger: "#E57373", disgust: "#BA68C8", fear: "#FFB74D",
  happy: "#81C784", sad: "#64B5F6", neutral: "#9E9E9E",
};

export function parseJsonl(text) {
  return text.trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
}

function speakerFor(speakers, faceId) {
  return (speakers && speakers.speakers && (speakers.speakers[faceId] || speakers.speakers.unknown))
    || { name: faceId || "Someone", color: "#9E9E9E" };
}

/** Group caption/tone_result events into per-speaker lanes, each caption row
 * carrying its tone tag (if any) and a DOM id so markers can scroll to it. */
export function buildLanes(container, events, speakers) {
  container.innerHTML = "";
  const toneByCaption = {};
  for (const e of events) {
    if (e.type === "tone_result" && e.tag) toneByCaption[e.caption_id] = e.tag;
  }
  const bySpeaker = new Map();
  for (const e of events) {
    if (e.type !== "caption") continue;
    const key = e.speaker_id || "unknown";
    if (!bySpeaker.has(key)) bySpeaker.set(key, []);
    bySpeaker.get(key).push(e);
  }
  for (const [faceId, captions] of bySpeaker) {
    const spk = speakerFor(speakers, faceId);
    const lane = document.createElement("div");
    lane.className = "lane";
    lane.style.borderLeftColor = spk.color;
    const heading = document.createElement("div");
    heading.style.color = spk.color;
    heading.style.fontWeight = "600";
    heading.textContent = spk.name;
    lane.appendChild(heading);
    for (const cap of captions) {
      const row = document.createElement("div");
      row.className = "caption-row";
      row.id = `caption-${cap.caption_id}`;
      const time = document.createElement("span");
      time.className = "caption-time";
      time.textContent = formatT(cap.t_start);
      row.appendChild(time);
      row.appendChild(document.createTextNode(cap.text));
      const tag = toneByCaption[cap.caption_id];
      if (tag) {
        const toneSpan = document.createElement("span");
        toneSpan.className = "caption-tone";
        toneSpan.textContent = `sounded ${tag}? (model guess)`;
        row.appendChild(toneSpan);
      }
      lane.appendChild(row);
    }
    container.appendChild(lane);
  }
}

function formatT(t) {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

/** Chart.js line chart of each tone_result's probs over time. */
export function buildToneChart(canvas, events) {
  const toneEvents = events.filter((e) => e.type === "tone_result" && e.probs);
  const labels = toneEvents.map((e) => formatT(e.t_start ?? captionStart(events, e.caption_id)));
  const tones = Object.keys(TONE_COLOR);
  const datasets = tones.map((tone) => ({
    label: tone,
    borderColor: TONE_COLOR[tone],
    backgroundColor: TONE_COLOR[tone],
    data: toneEvents.map((e) => e.probs[tone] ?? 0),
    tension: 0.3,
    pointRadius: 2,
  }));
  // Chart.js comes from a CDN; offline (demo with Wi-Fi off) it is missing. Skip the chart, keep the page.
  if (typeof Chart === "undefined") {
    const note = canvas.parentElement?.querySelector(".chart-offline");
    if (!note && canvas.parentElement) {
      const p = document.createElement("p");
      p.className = "chart-offline recap-status";
      p.textContent = "Tone chart unavailable offline (Chart.js not loaded).";
      canvas.parentElement.appendChild(p);
    }
    return null;
  }
  // eslint-disable-next-line no-undef
  return new Chart(canvas, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      scales: { y: { min: 0, max: 1, ticks: { color: "#999" } }, x: { ticks: { color: "#999" } } },
      plugins: { legend: { labels: { color: "#ccc" } } },
    },
  });
}

function captionStart(events, captionId) {
  const cap = events.find((e) => e.type === "caption" && e.caption_id === captionId);
  return cap ? cap.t_start : 0;
}

function eventT(e) {
  if (e.type === "sound_event") return e.t;
  if (e.type === "social_cue") return e.t;
  return 0;
}

/** Sound/social_cue markers on a horizontal strip; clicking one scrolls its
 * related caption into view and highlights it briefly. */
export function buildMarkers(container, events) {
  container.innerHTML = "";
  const markerEvents = events.filter((e) => e.type === "sound_event" || e.type === "social_cue");
  if (markerEvents.length === 0) return;
  const maxT = Math.max(...markerEvents.map(eventT), 1);
  for (const e of markerEvents) {
    const dot = document.createElement("div");
    dot.className = "marker " + (e.type === "sound_event" ? "marker-sound" : "marker-cue");
    dot.style.left = `${(eventT(e) / maxT) * 96}%`;
    dot.title = e.type === "sound_event" ? e.label : e.cue;
    dot.addEventListener("click", () => scrollToCaption(events, e));
    container.appendChild(dot);
  }
}

function scrollToCaption(events, markerEvent) {
  let captionId = markerEvent.related_caption_id;
  if (!captionId) {
    // Fall back to the nearest preceding caption by time.
    const t = eventT(markerEvent);
    let best = null;
    for (const e of events) {
      if (e.type !== "caption") continue;
      if (e.t_start <= t && (!best || e.t_start > best.t_start)) best = e;
    }
    captionId = best && best.caption_id;
  }
  if (!captionId) return;
  const row = document.getElementById(`caption-${captionId}`);
  if (!row) return;
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.add("highlight");
  setTimeout(() => row.classList.remove("highlight"), 1500);
}

/** Replay: re-reveal events in order using their _replay_t deltas (sample log)
 * or evenly spaced if absent, flashing each marker/caption as it "arrives". */
export function replay(events, onEvent, { speed = 4 } = {}) {
  let prevT = events[0] ? events[0]._replay_t ?? 0 : 0;
  let delay = 0;
  for (const e of events) {
    const t = e._replay_t ?? prevT;
    delay += Math.max(0, (t - prevT) * 1000) / speed;
    prevT = t;
    setTimeout(() => onEvent(e), delay);
  }
}

const SOURCE_LABEL = { grok: "Grok", heuristic: "Rule-based", canned: "Canned" };

function recapSection(title, bodyEl) {
  const wrap = document.createElement("div");
  wrap.className = "recap-subsection";
  const heading = document.createElement("h3");
  heading.textContent = title;
  wrap.append(heading, bodyEl);
  return wrap;
}

function recapList(items, renderItem) {
  const ul = document.createElement("ul");
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.className = "recap-empty";
    li.textContent = "None";
    ul.appendChild(li);
    return ul;
  }
  for (const item of items) {
    const li = document.createElement("li");
    li.appendChild(renderItem(item));
    ul.appendChild(li);
  }
  return ul;
}

/** Render the catch-me-up response without replacing the timeline UI. */
export function renderRecap(container, response) {
  container.innerHTML = "";
  const badge = document.createElement("span");
  badge.className = "source-badge source-" + response.source;
  badge.textContent = SOURCE_LABEL[response.source] || response.source;
  container.appendChild(badge);

  if (response.message) {
    const message = document.createElement("div");
    message.className = "recap-message";
    message.textContent = response.message;
    container.appendChild(message);
  }

  const recap = response.recap;
  const summary = document.createElement("p");
  summary.textContent = recap.overall_summary;
  container.appendChild(recapSection("Summary", summary));

  container.appendChild(recapSection("Addressed to you", recapList(recap.addressed_to_you, (item) => {
    const el = document.createElement("div");
    const time = document.createElement("span");
    time.className = "caption-time";
    time.textContent = item.t;
    const text = document.createElement("span");
    text.textContent = `${item.speaker}: "${item.quote}" — needs: ${item.what_they_need}`;
    el.append(time, text);
    return el;
  })));

  const textList = (items, format) => recapList(items, (item) => {
    const el = document.createElement("span");
    el.textContent = format(item);
    return el;
  });
  container.appendChild(recapSection("Per speaker", textList(recap.per_speaker, (item) => `${item.speaker}: ${item.summary}`)));
  container.appendChild(recapSection("Action items", textList(recap.action_items, (item) => `${item.owner}: ${item.item}` + (item.due ? ` (due ${item.due})` : ""))));
  container.appendChild(recapSection("Tone highlights", textList(recap.tone_highlights, (item) => `${item.t} ${item.speaker} ${item.tone} — ${item.note}`)));

  const disclaimer = document.createElement("p");
  disclaimer.className = "recap-disclaimer";
  disclaimer.textContent = recap.disclaimer;
  container.appendChild(disclaimer);
}

export async function fetchRecap(sessionId, { mockFixtureUrl } = {}) {
  if (mockFixtureUrl) {
    const response = await fetch(mockFixtureUrl);
    if (!response.ok) throw new Error(`recap fixture failed: ${response.status}`);
    return response.json();
  }
  const response = await fetch("/api/recap", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!response.ok) throw new Error(`recap failed: ${response.status}`);
  return response.json();
}
