/* Catch-me-up rendering: turns a RecapResponse ({source, recap, message}) into
 * DOM, with "Addressed to you" first, a source tag, and the standard disclaimer. */

const SOURCE_LABEL = { grok: "Grok", heuristic: "Rule-based", canned: "Canned" };

function section(title, bodyEl) {
  const wrap = document.createElement("div");
  wrap.className = "recap-subsection";
  const h = document.createElement("h3");
  h.textContent = title;
  wrap.appendChild(h);
  wrap.appendChild(bodyEl);
  return wrap;
}

function list(items, renderItem) {
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

/** POST /api/recap's response (or its mock equivalent) -> a rendered catch-me-up panel. */
export function renderRecap(container, response) {
  container.innerHTML = "";

  const badge = document.createElement("span");
  badge.className = "source-badge source-" + response.source;
  badge.textContent = SOURCE_LABEL[response.source] || response.source;
  container.appendChild(badge);

  if (response.message) {
    const msg = document.createElement("div");
    msg.className = "recap-message";
    msg.textContent = response.message;
    container.appendChild(msg);
  }

  const recap = response.recap;

  const summary = document.createElement("p");
  summary.textContent = recap.overall_summary;
  container.appendChild(section("Summary", summary));

  container.appendChild(section("Addressed to you", list(recap.addressed_to_you, (a) => {
    const el = document.createElement("div");
    el.innerHTML = "";
    const time = document.createElement("span");
    time.className = "caption-time";
    time.textContent = a.t;
    el.appendChild(time);
    const text = document.createElement("span");
    text.textContent = `${a.speaker}: "${a.quote}" — needs: ${a.what_they_need}`;
    el.appendChild(text);
    return el;
  })));

  container.appendChild(section("Per speaker", list(recap.per_speaker, (p) => {
    const el = document.createElement("span");
    el.textContent = `${p.speaker}: ${p.summary}`;
    return el;
  })));

  container.appendChild(section("Action items", list(recap.action_items, (a) => {
    const el = document.createElement("span");
    el.textContent = `${a.owner}: ${a.item}` + (a.due ? ` (due ${a.due})` : "");
    return el;
  })));

  container.appendChild(section("Tone highlights", list(recap.tone_highlights, (t) => {
    const el = document.createElement("span");
    el.textContent = `${t.t} ${t.speaker} ${t.tone} — ${t.note}`;
    return el;
  })));

  const disclaimer = document.createElement("p");
  disclaimer.className = "recap-disclaimer";
  disclaimer.textContent = recap.disclaimer;
  container.appendChild(disclaimer);
}

/** Fetch the recap for `sessionId`: real POST /api/recap, or (session === "sample"
 * with no backend reachable) a mock fixture passed in by the caller. */
export async function fetchRecap(sessionId, { mockFixtureUrl } = {}) {
  if (mockFixtureUrl) {
    const res = await fetch(mockFixtureUrl);
    return res.json();
  }
  const res = await fetch("/api/recap", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`recap failed: ${res.status}`);
  return res.json();
}
