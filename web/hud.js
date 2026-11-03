/* HUD panel renderer: draws a Hud's DisplayNode tree (CONTRACTS.md) into a 600x600
 * black rounded panel styled like the Ray-Ban Display, and fades it out after ttl_s. */

const STYLE_CLASS = { heading: "hud-heading", body: "hud-body", meta: "hud-meta" };

function renderNode(node) {
  if (node.kind === "Text") {
    const el = document.createElement("div");
    el.className = STYLE_CLASS[node.style] || "hud-body";
    if (node.color === "secondary") el.classList.add("hud-secondary");
    el.textContent = node.text || "";
    return el;
  }
  if (node.kind === "Icon") {
    const el = document.createElement("div");
    el.className = "hud-icon";
    el.dataset.icon = node.name || "";
    el.textContent = "●";
    if (node.color) el.style.color = node.color;
    return el;
  }
  // FlexBox
  const el = document.createElement("div");
  el.className = "hud-flex hud-flex-" + (node.direction || "column");
  for (const child of node.children || []) el.appendChild(renderNode(child));
  return el;
}

let fadeTimer = null;

/** Draw `hud` (a Hud dict, or null to clear) into `el`, the 600x600 panel container. */
export function renderHud(el, hud) {
  if (fadeTimer) {
    clearTimeout(fadeTimer);
    fadeTimer = null;
  }
  el.innerHTML = "";
  el.classList.remove("hud-fade-out");
  if (!hud) {
    el.classList.add("hud-empty");
    return;
  }
  el.classList.remove("hud-empty");
  el.appendChild(renderNode(hud.tree));
  const ttlMs = (hud.ttl_s || 4) * 1000;
  fadeTimer = setTimeout(() => {
    el.classList.add("hud-fade-out");
  }, ttlMs);
}
