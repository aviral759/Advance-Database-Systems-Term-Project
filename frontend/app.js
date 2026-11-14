"use strict";

/* ==========================================================================
   Hybrid Photo Library · frontend
   A photo application on the surface, an intelligent retrieval engine underneath.
   Framework-free · static (no animation) · light + dark themes
   ========================================================================== */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/* ---------------------------------------------------------------- icons (Lucide-style) */
const ICONS = {
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/>',
  sparkles: '<path d="M12 3l1.9 4.7L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.8z"/><path d="M19 15.5l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>',
  images: '<rect x="7" y="7" width="14" height="13" rx="2"/><path d="M3 16V6a2 2 0 0 1 2-2h11"/><circle cx="12" cy="11.5" r="1.5"/><path d="M21 17l-4-4-6 6"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
  star: '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8L3.5 9.7l5.9-.9z"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  pin: '<path d="M12 21s-6.5-6.2-6.5-11a6.5 6.5 0 0 1 13 0c0 4.8-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/>',
  tag: '<path d="M3 12.5V4h8.5L21 13.5 13.5 21z"/><circle cx="7.5" cy="8.5" r="1.3"/>',
  folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  upload: '<path d="M12 15V4"/><path d="M7.5 8.5L12 4l4.5 4.5"/><path d="M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15"/>',
  flow: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><path d="M6.5 10v2.5a3 3 0 0 0 3 3H14"/>',
  gauge: '<path d="M4 16a8 8 0 1 1 16 0"/><path d="M12 16l4-5"/><circle cx="12" cy="16" r="1.2"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 13.5a7.6 7.6 0 0 0 0-3l2-1.6-2-3.4-2.4.9a7.5 7.5 0 0 0-2.6-1.5L14 2.5h-4l-.4 2.4a7.5 7.5 0 0 0-2.6 1.5l-2.4-.9-2 3.4 2 1.6a7.6 7.6 0 0 0 0 3l-2 1.6 2 3.4 2.4-.9a7.5 7.5 0 0 0 2.6 1.5l.4 2.4h4l.4-2.4a7.5 7.5 0 0 0 2.6-1.5l2.4.9 2-3.4z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.6 4.6l1.4 1.4M18 18l1.4 1.4M2.5 12h2M19.5 12h2M4.6 19.4L6 18M18 6l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  camera: '<path d="M4 8h3.2l1.8-2.5h6L16.8 8H20v11H4z"/><circle cx="12" cy="13.2" r="3.4"/>',
  external: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v4.5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6H10"/>',
  copy: '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5.5A1.5 1.5 0 0 1 6.5 4H15"/>',
  trash: '<path d="M4 7h16"/><path d="M10 11v6M14 11v6"/><path d="M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12"/><path d="M9 7V4h6v3"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17.5h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  zoomIn: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6M11 8v6M8 11h6"/>',
  zoomOut: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6M8 11h6"/>',
  fit: '<path d="M4 9V5a1 1 0 0 1 1-1h4M15 4h4a1 1 0 0 1 1 1v4M20 15v4a1 1 0 0 1-1 1h-4M9 20H5a1 1 0 0 1-1-1v-4"/>',
  chevron: '<path d="M9 6l6 6-6 6"/>',
  database: '<ellipse cx="12" cy="6" rx="7.5" ry="3"/><path d="M4.5 6v12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V6"/><path d="M4.5 12c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
  aperture: '<circle cx="12" cy="12" r="9"/><path d="M14.3 3.3L9 12M20.6 9H11M17.6 18.7L13 10.9M9.7 20.7L15 12M3.4 15H13M6.4 5.3L11 13.1"/>',
  refresh: '<path d="M20 11a8 8 0 0 0-14.9-3"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.9 3"/><path d="M20 20v-4h-4"/>',
  play: '<path d="M7 4.5v15l12-7.5z"/>',
  grid: '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
  gridsm: '<path d="M4 4h4v4H4zM10 4h4v4h-4zM16 4h4v4h-4zM4 10h4v4H4zM10 10h4v4h-4zM16 10h4v4h-4zM4 16h4v4H4zM10 16h4v4h-4zM16 16h4v4h-4z"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  bolt: '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>',
  pulse: '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
  compare: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M12 5v14"/>',
  shield: '<path d="M12 3l7 3v5c0 4.5-3 8.3-7 10-4-1.7-7-5.5-7-10V6z"/>',
  box: '<rect x="4" y="4" width="16" height="16" rx="2" stroke-dasharray="3 2.5"/>',
  file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
};
const svgIcon = (name) =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
const icon = (name, cls = "") => `<span class="icon ${cls}">${svgIcon(name)}</span>`;
function hydrateIcons(root = document) {
  $$("[data-icon]", root).forEach((el) => {
    el.innerHTML = svgIcon(el.dataset.icon);
    el.classList.add("icon");
    el.removeAttribute("data-icon");
  });
}

/* ---------------------------------------------------------------- persistence (this browser) */
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); }
    catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ }
  },
};
const DEFAULTS = { theme: "light", k: 24, lexw: 0.05, mode: "auto", density: "comfortable" };
const settings = { ...DEFAULTS, ...store.get("hps.settings", {}) };
const saveSettings = () => store.set("hps.settings", settings);
const favorites = new Set(store.get("hps.favorites", []).map(Number));
function saveFavorites() { store.set("hps.favorites", [...favorites]); updateFavCount(); }

/* ---------------------------------------------------------------- constants */
const STRAT = {
  filter_first: { label: "Filter-first", cls: "ff" },
  vector_first: { label: "Vector-first", cls: "vf" },
  vector_only: { label: "Vector-only", cls: "vf" },
  metadata_only: { label: "Metadata-only", cls: "md" },
  empty: { label: "Empty index", cls: "md" },
};
const BUCKETS = [
  ["encode", "Encode (OpenCLIP)"], ["planning", "Planning"], ["sqlite", "SQLite"], ["faiss", "FAISS HNSW"],
  ["exact", "Exact rerank"], ["fusion", "Score fusion"], ["fetch", "Row fetch"],
];
const BUCKET_LABEL = Object.fromEntries(BUCKETS);
const bucketColor = (k) => `var(--c-${k || "fetch"})`;
const EXAMPLES = [
  "a dog playing on a beach tag:dog after:2013",
  "people riding bikes in a city",
  "a person walking down a street tag:person",
  "food on a kitchen counter tag:toaster",
  "a dog object:dog region:0,0,0.5,1",
  "a busy street near:51.507,-0.128,40",
];
const PAGES = {
  search: ["Library", "Search"], ingest: ["System", "Ingest"], plan: ["System", "Execution plan"],
  system: ["System", "System overview"], settings: ["System", "Settings"],
};
const REGION_PRESETS = [
  ["Left half", [0, 0, 0.5, 1]], ["Right half", [0.5, 0, 1, 1]], ["Top half", [0, 0, 1, 0.5]],
  ["Bottom half", [0, 0.5, 1, 1]], ["Centre", [0.25, 0.25, 0.75, 0.75]],
];
const ORIGIN_LABEL = { manual: "Added by you", annotation: "Dataset annotation", clip: "AI-generated (CLIP zero-shot)" };
const COST_DOC = {
  sql_fixed_ms: "Fixed cost per SQL statement", sql_row_ms: "Per candidate row read from SQLite",
  gather_row_ms: "Per vector gathered from RAM", dot_ms_per_dim: "Per multiply-add in exact scoring",
  hnsw_fixed_ms: "Fixed cost per HNSW search", hnsw_ef_ms: "Per unit of efSearch",
  verify_id_ms: "Per HNSW id verified in SQL", safety: "Over-fetch factor α",
  degenerate_ratio: "Max k′/N before vector-first is rejected",
};

const state = {
  route: "search", stats: null, collections: null, readOnly: false,
  lastData: null, results: [], lastRun: null, history: [], planIndex: 0, compare: null,
  region: null, pills: [], queue: [], tallies: { ok: 0, dup: 0, err: 0 },
  current: null, selectedObj: null, zoom: 1, fitW: 0,
  library: { mode: "all", value: "", offset: 0, total: 0, items: [] },
};

/* ---------------------------------------------------------------- utils */
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 2) => (v === null || v === undefined || Number.isNaN(Number(v)) ? "—" : Number(v).toFixed(d));
const pct = (v) => {
  if (v === null || v === undefined) return "—";
  const x = v * 100;
  return x > 0 && x < 0.01 ? "<0.01%" : `${x.toFixed(x < 1 ? 2 : 1)}%`;
};
const bytes = (n) => {
  if (n === null || n === undefined) return "—";
  const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0; let x = n;
  while (x >= 1024 && i < u.length - 1) { x /= 1024; i++; }
  return `${x.toFixed(i ? 1 : 0)} ${u[i]}`;
};
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const splitList = (v) => v.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
const fmtDate = (iso) => {
  if (!iso) return "Undated";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso.slice(0, 10) : d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
};
const fmtTime = (d) => d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const fmtDuration = (s) => (s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`);
const fmtCoord = (lat, lon) => `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? "N" : "S"}, ${Math.abs(lon).toFixed(2)}°${lon >= 0 ? "E" : "W"}`;
const stratInfo = (s) => STRAT[s] || { label: s || "—", cls: "md" };
const stratBadge = (s) => { const i = stratInfo(s); return `<span class="strat ${i.cls}">${esc(i.label)}</span>`; };
const modelShort = (id) => (id || "").split(":")[1] || id || "—";
const emptyState = (ic, title, text, action = "") =>
  `<div class="empty-state">${icon(ic, "empty-icon")}<div class="empty-title">${esc(title)}</div><div class="empty-text">${esc(text)}</div>${action}</div>`;
const alertHTML = (msg, kind = "err") => `<div class="alert ${kind}">${icon("alert")}<div>${esc(msg)}</div></div>`;
const kv = (rows) =>
  `<dl class="kv">${rows.map(([k, v, html]) => `<dt>${esc(k)}</dt><dd>${v === null || v === undefined || v === "" ? '<span class="dim">—</span>' : html ? v : esc(v)}</dd>`).join("")}</dl>`;

async function api(path, options = {}) {
  const res = await fetch(path, { credentials: "same-origin", ...options });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = body.detail;
    throw new Error(typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg || JSON.stringify(x)).join("; ") : `HTTP ${res.status}`);
  }
  return body;
}
const jsonPost = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

function toast(message, kind = "info") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = `${icon(kind === "err" ? "alert" : kind === "ok" ? "check" : "info")}<span>${esc(message)}</span>`;
  $("#toasts").appendChild(el);
  setTimeout(() => el.remove(), 3800);
}

/* ---------------------------------------------------------------- theme & density */
function applyTheme() {
  document.documentElement.dataset.theme = settings.theme;
  $("#theme-toggle").innerHTML = svgIcon(settings.theme === "dark" ? "sun" : "moon");
  $$("#set-theme .seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.value === settings.theme));
}
function applyDensity() {
  ["#grid", "#lib-grid"].forEach((sel) => $(sel).classList.toggle("compact", settings.density === "compact"));
  $$(".density-seg .seg-btn").forEach((b) => b.classList.toggle("active", b.dataset.density === settings.density));
}
$("#theme-toggle").addEventListener("click", () => { settings.theme = settings.theme === "dark" ? "light" : "dark"; saveSettings(); applyTheme(); });
$$("#set-theme .seg-btn").forEach((b) => b.addEventListener("click", () => { settings.theme = b.dataset.value; saveSettings(); applyTheme(); }));
$$(".density-seg .seg-btn").forEach((b) => b.addEventListener("click", () => { settings.density = b.dataset.density; saveSettings(); applyDensity(); }));

/* ---------------------------------------------------------------- routing */
function setHeader(crumb, title) {
  $("#crumbs").textContent = crumb;
  $("#page-title").textContent = title;
}
function go(route) {
  const [view, mode = "", ...rest] = route.split(":");
  const value = rest.join(":");
  state.route = route;
  $$(".nav-item").forEach((b) => b.classList.toggle("active",
    b.dataset.route === route || (route.startsWith("library:places") && b.dataset.route === "library:places")));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  $("#quick-search").classList.toggle("hidden", view === "search");
  if (view === "library") openLibrary(mode || "all", value);
  else setHeader(...(PAGES[view] || ["", view]));
  if (view === "plan") renderPlan();
  if (view === "system") loadSystem();
  if (view === "settings") renderSettings();
  closeDrawer();
  window.scrollTo(0, 0);
}
document.addEventListener("click", (e) => {
  const r = e.target.closest("[data-route]");
  if (r) { e.preventDefault(); go(r.dataset.route); return; }
  const o = e.target.closest("[data-open]");
  if (o) openInspector(Number(o.dataset.open));
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#drawer").classList.contains("hidden")) { closeDrawer(); return; }
  const tag = document.activeElement?.tagName;
  if (e.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(tag)) { e.preventDefault(); go("search"); $("#q").focus(); }
});
$("#quick-search").addEventListener("submit", (e) => {
  e.preventDefault();
  $("#q").value = $("#quick-q").value;
  $("#quick-q").value = "";
  go("search");
  runSearch();
});

/* ---------------------------------------------------------------- stats & status */
async function loadStats() {
  try { const s = await api("/api/stats"); applyStats(s); return s; }
  catch {
    $("#health .dot").className = "dot err";
    $("#health-text").textContent = "Offline";
    return null;
  }
}
function applyStats(s) {
  state.stats = s;
  state.readOnly = !!s.server.read_only;
  const ok = s.health?.status === "ok";
  $("#health .dot").className = `dot ${ok ? "ok" : "err"}`;
  $("#health-text").textContent = ok ? `${s.library.photos.toLocaleString()} photos indexed` : "Degraded";
  const st = s.storage;
  const parts = [
    ["Images", st.images_bytes, "var(--accent)"], ["Thumbnails", st.thumbs_bytes, "var(--teal)"],
    ["Database", (st.db_bytes || 0) + (st.wal_bytes || 0), "var(--violet)"], ["Vector index", s.vector_index.index_file_bytes, "var(--amber)"],
  ];
  const total = parts.reduce((a, p) => a + (p[1] || 0), 0) || 1;
  $("#storage-total").textContent = bytes(total);
  $("#storage-bar").innerHTML = parts.map(([, b, c]) => `<span style="width:${((b || 0) / total * 100).toFixed(2)}%;background:${c}"></span>`).join("");
  $("#storage-legend").innerHTML = parts.map(([l, b, c]) => `<span><i style="background:${c}"></i>${esc(l)} ${bytes(b || 0)}</span>`).join("");
  $("#storage-foot").textContent = st.disk_total ? `Disk ${Math.round(st.disk_used / st.disk_total * 100)}% used · ${bytes(st.disk_free)} free` : "";
  $("#tag-options").innerHTML = s.top_tags.map((t) => `<option value="${esc(t.name)}">`).join("");
  const sel = $("#f-source"); const cur = sel.value;
  sel.innerHTML = '<option value="">Any source</option>' + Object.keys(s.library.sources).map((k) => `<option value="${esc(k)}">${esc(k)}</option>`).join("");
  sel.value = cur;
  $("#cfg-model").textContent = modelShort(s.embedding.model_id);
  $("#ro-notice").classList.toggle("hidden", !state.readOnly);
  renderQueue();
}
async function loadCollections() {
  try {
    state.collections = await api("/api/collections");
    const c = state.collections;
    const tags = c.tags.filter((t) => t.name !== "synthetic-geo").slice(0, 6);
    const html = tags.map((t) => `<button class="nav-item sub" data-route="library:tag:${esc(t.name)}">${icon("tag")}<span class="label">${esc(t.name)}</span><span class="nav-count">${t.count}</span></button>`).join("")
      + c.sources.slice(0, 4).map((s) => `<button class="nav-item sub" data-route="library:source:${esc(s.name)}">${icon("folder")}<span class="label">${esc(s.name)}</span><span class="nav-count">${s.count}</span></button>`).join("");
    $("#nav-collections").innerHTML = html || '<div class="nav-empty">No collections yet</div>';
    $$("#nav-collections .nav-item").forEach((b) => b.classList.toggle("active", b.dataset.route === state.route));
  } catch {
    $("#nav-collections").innerHTML = '<div class="nav-empty">Unavailable</div>';
  }
}
function updateFavCount() { $("#fav-count").textContent = favorites.size || ""; }

/* ---------------------------------------------------------------- search controls */
function renderExamples() {
  $("#examples").innerHTML = '<span class="ex-label">Try</span>' +
    EXAMPLES.map((q, i) => `<button type="button" class="ex-chip" data-ex="${i}">${esc(q)}</button>`).join("");
}
$("#examples").addEventListener("click", (e) => {
  const b = e.target.closest("[data-ex]");
  if (!b) return;
  $("#q").value = EXAMPLES[Number(b.dataset.ex)];
  runSearch();
});
$("#search-form").addEventListener("submit", (e) => { e.preventDefault(); runSearch(); });
$("#clear-q").addEventListener("click", () => { $("#q").value = ""; $("#q").focus(); });
$("#kind-text").addEventListener("click", () => $("#q").focus());
$("#toggle-filters").addEventListener("click", () => {
  $("#filter-panel").classList.toggle("hidden");
  $("#toggle-filters").classList.toggle("on", !$("#filter-panel").classList.contains("hidden"));
});
$("#filters-apply").addEventListener("click", () => runSearch());
$("#filters-reset").addEventListener("click", () => { resetFilters(); runSearch(); });
$$("#filter-panel input, #filter-panel select").forEach((el) => {
  el.addEventListener("input", renderActiveFilters);
  el.addEventListener("change", renderActiveFilters);
  el.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); runSearch(); } });
});
$("#sort").addEventListener("change", renderGrid);
$("#min-sim").addEventListener("input", () => { $("#min-sim-val").textContent = Number($("#min-sim").value).toFixed(2); renderGrid(); });

function collectFilters() {
  const f = {};
  const tags = splitList($("#f-tags").value); if (tags.length) f.tags = tags;
  const objects = splitList($("#f-objects").value); if (objects.length) f.objects = objects;
  if ($("#f-from").value) f.date_from = $("#f-from").value;
  if ($("#f-to").value) f.date_to = $("#f-to").value;
  if ($("#f-camera").value.trim()) f.camera = $("#f-camera").value.trim();
  if ($("#f-text").value.trim()) f.text = $("#f-text").value.trim();
  if ($("#f-source").value) f.source = $("#f-source").value;
  const lat = $("#f-lat").value; const lon = $("#f-lon").value; const km = $("#f-km").value;
  if (lat !== "" && lon !== "") {
    f.near_lat = Number(lat); f.near_lon = Number(lon);
    if (km !== "" && Number(km) > 0) f.near_km = Number(km);
  }
  if (state.region) f.region = state.region;
  return f;
}
function filterPills() {
  const pills = [];
  const add = (label, clear) => pills.push({ label, clear });
  splitList($("#f-tags").value).forEach((t) => add(`Tag: ${t}`, () => { $("#f-tags").value = splitList($("#f-tags").value).filter((x) => x !== t).join(", "); }));
  splitList($("#f-objects").value).forEach((o) => add(`Object: ${o}`, () => { $("#f-objects").value = splitList($("#f-objects").value).filter((x) => x !== o).join(", "); }));
  if ($("#f-from").value) add(`From ${$("#f-from").value}`, () => { $("#f-from").value = ""; });
  if ($("#f-to").value) add(`Until ${$("#f-to").value}`, () => { $("#f-to").value = ""; });
  if ($("#f-camera").value.trim()) add(`Camera: ${$("#f-camera").value.trim()}`, () => { $("#f-camera").value = ""; });
  if ($("#f-text").value.trim()) add(`Keyword: ${$("#f-text").value.trim()}`, () => { $("#f-text").value = ""; });
  if ($("#f-source").value) add(`Source: ${$("#f-source").value}`, () => { $("#f-source").value = ""; });
  if ($("#f-lat").value !== "" && $("#f-lon").value !== "") {
    add(`Within ${$("#f-km").value || 25} km of ${$("#f-lat").value}, ${$("#f-lon").value}`, () => { $("#f-lat").value = ""; $("#f-lon").value = ""; $("#f-km").value = ""; });
  }
  if (state.region) {
    const r = state.region;
    add(`Region x ${r[0].toFixed(2)}–${r[2].toFixed(2)}, y ${r[1].toFixed(2)}–${r[3].toFixed(2)}`, () => { state.region = null; renderRegion(); });
  }
  return pills;
}
function renderActiveFilters() {
  const pills = filterPills();
  state.pills = pills;
  $("#filter-count").textContent = pills.length;
  $("#filter-count").classList.toggle("hidden", !pills.length);
  $("#active-filters").innerHTML = pills.length
    ? pills.map((p, i) => `<span class="af-pill">${esc(p.label)}<button type="button" data-clear="${i}" aria-label="Remove filter">${icon("x")}</button></span>`).join("") +
      '<button type="button" class="link small" id="af-clear-all">Clear all</button>'
    : "";
}
$("#active-filters").addEventListener("click", (e) => {
  const b = e.target.closest("[data-clear]");
  if (b) { state.pills[Number(b.dataset.clear)].clear(); renderActiveFilters(); runSearch(); return; }
  if (e.target.closest("#af-clear-all")) { resetFilters(); runSearch(); }
});
function resetFilters() {
  ["#f-tags", "#f-objects", "#f-from", "#f-to", "#f-camera", "#f-text", "#f-lat", "#f-lon", "#f-km"].forEach((id) => { $(id).value = ""; });
  $("#f-source").value = "";
  state.region = null;
  renderRegion();
  renderActiveFilters();
}

/* region picker */
function renderRegionPresets() {
  $("#region-presets").innerHTML = REGION_PRESETS.map(([label], i) => `<button type="button" class="ex-chip" data-preset="${i}">${esc(label)}</button>`).join("");
}
$("#region-presets").addEventListener("click", (e) => {
  const b = e.target.closest("[data-preset]");
  if (!b) return;
  state.region = REGION_PRESETS[Number(b.dataset.preset)][1].slice();
  renderRegion(); renderActiveFilters();
});
function renderRegion(draft) {
  const r = draft || state.region;
  const rect = $("#region-rect");
  if (!r) {
    rect.classList.add("hidden");
    $("#region-values").innerHTML = '<span class="dim">No region: objects may be anywhere in the frame.</span>';
    return;
  }
  Object.assign(rect.style, { left: `${r[0] * 100}%`, top: `${r[1] * 100}%`, width: `${(r[2] - r[0]) * 100}%`, height: `${(r[3] - r[1]) * 100}%` });
  rect.classList.remove("hidden");
  $("#region-values").innerHTML = `<span class="mono">x ${r[0].toFixed(2)}–${r[2].toFixed(2)} · y ${r[1].toFixed(2)}–${r[3].toFixed(2)}</span> &nbsp;<button type="button" class="link small" id="region-clear">Clear region</button>`;
}
$("#region-values").addEventListener("click", (e) => {
  if (e.target.closest("#region-clear")) { state.region = null; renderRegion(); renderActiveFilters(); }
});
(() => {
  const pad = $("#region-pad");
  let start = null; let draft = null;
  const point = (e) => { const b = pad.getBoundingClientRect(); return [clamp01((e.clientX - b.left) / b.width), clamp01((e.clientY - b.top) / b.height)]; };
  const toRegion = (a, b) => [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])].map((v) => Math.round(v * 1000) / 1000);
  pad.addEventListener("pointerdown", (e) => { start = point(e); draft = toRegion(start, start); pad.setPointerCapture(e.pointerId); renderRegion(draft); });
  pad.addEventListener("pointermove", (e) => { if (!start) return; draft = toRegion(start, point(e)); renderRegion(draft); });
  pad.addEventListener("pointerup", () => {
    if (!start) return;
    start = null;
    state.region = draft && draft[2] - draft[0] > 0.03 && draft[3] - draft[1] > 0.03 ? draft : null;
    renderRegion(); renderActiveFilters();
  });
})();

/* ---------------------------------------------------------------- query execution */
async function runSearch() {
  const q = $("#q").value.trim();
  const filters = collectFilters();
  renderActiveFilters();
  const base = { q, filters, k: Number(settings.k), lexical_weight: Number(settings.lexw) };
  const label = q ? `“${q}”` : Object.keys(filters).length ? "Filtered browse" : "Browse latest photos";
  setKind("text");
  await execute({ label, banner: null, run: (mode) => jsonPost("/api/search", { ...base, mode }) });
}
async function findSimilar(id) {
  closeDrawer();
  if (state.route !== "search") go("search");
  await execute({
    label: `Similar to photo #${id}`,
    banner: { thumb: `/api/photos/${id}/thumb`, title: `Photos similar to #${id}`, sub: "Image-to-image search with the stored OpenCLIP embedding. Active filters still apply." },
    run: (mode) => jsonPost("/api/similar", { photo_id: id, k: Number(settings.k), filters: collectFilters(), mode }),
  });
}
$("#img-query").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  setKind("image");
  await execute({
    label: `Image search · ${file.name}`,
    banner: { thumb: URL.createObjectURL(file), title: `Image search: ${file.name}`, sub: "The image is embedded with OpenCLIP but not added to your library." },
    run: (mode) => {
      const fd = new FormData();
      fd.append("file", file); fd.append("k", settings.k); fd.append("mode", mode);
      return api("/api/similar/upload", { method: "POST", body: fd });
    },
  });
  e.target.value = "";
});
function setKind(kind) {
  $("#kind-text").classList.toggle("active", kind === "text");
  $("#kind-image").classList.toggle("active", kind === "image");
}

function pushHistory(label, data) {
  state.history.unshift({ label, plan: data.plan, query: data.query || {}, at: new Date() });
  state.history = state.history.slice(0, 25);
  state.planIndex = 0;
  state.compare = null;
  const pill = $("#nav-plan-pill");
  pill.textContent = stratInfo(data.plan.strategy).label;
  pill.classList.remove("hidden");
}
async function execute(req) {
  const btn = $("#search-btn");
  btn.disabled = true; btn.textContent = "Searching…";
  $("#grid").classList.add("is-loading");
  try {
    const data = await req.run(settings.mode);
    state.lastRun = req;
    pushHistory(req.label, data);
    renderBanner(req.banner);
    renderResults(data);
  } catch (err) {
    $("#warnings").innerHTML = alertHTML(`Search failed: ${err.message}`);
  } finally {
    btn.disabled = false; btn.textContent = "Search";
    $("#grid").classList.remove("is-loading");
  }
}

function renderBanner(b) {
  const el = $("#banner");
  if (!b) { el.classList.add("hidden"); el.innerHTML = ""; return; }
  el.innerHTML = `${b.thumb ? `<img src="${esc(b.thumb)}" alt="">` : ""}
    <div class="banner-text"><div class="banner-title">${esc(b.title)}</div><div class="banner-sub">${esc(b.sub)}</div></div>
    <button type="button" class="btn" id="banner-clear">${icon("x")}Back to text search</button>`;
  el.classList.remove("hidden");
  $("#banner-clear").onclick = () => runSearch();
}

function parsedChips(query) {
  const f = query.filters || {};
  const chips = [];
  if (query.semantic_text) chips.push(["text", "Text", query.semantic_text]);
  if (query.photo_id) chips.push(["image", "Similar to", `#${query.photo_id}`]);
  if (query.uploaded_file) chips.push(["image", "Image", query.uploaded_file]);
  (f.tags || []).forEach((t) => chips.push(["filter", "Tag", t]));
  (f.objects || []).forEach((o) => chips.push(["filter", "Object", o]));
  if (f.date_from) chips.push(["filter", "After", f.date_from]);
  if (f.date_to) chips.push(["filter", "Before", f.date_to]);
  if (f.near) chips.push(["filter", "Near", `${f.near[0]}, ${f.near[1]} · ${f.near[2]} km`]);
  if (f.region) chips.push(["filter", "Region", f.region.map((v) => Number(v).toFixed(2)).join(", ")]);
  if (f.camera) chips.push(["filter", "Camera", f.camera]);
  if (f.text) chips.push(["filter", "Keyword", f.text]);
  if (f.source) chips.push(["filter", "Source", f.source]);
  return chips;
}
const chipsHTML = (chips) => chips.map(([kind, k, v]) => `<span class="qchip ${kind}"><span class="qk">${esc(k)}</span><span class="qv">${esc(v)}</span></span>`).join("");

function renderParsed(data) {
  const el = $("#parsed");
  const chips = parsedChips(data.query || {});
  if (!chips.length) { el.classList.add("hidden"); return; }
  const hasText = !!data.query.semantic_text || !!data.query.photo_id || !!data.query.uploaded_file;
  const hasFilters = chips.some((c) => c[0] === "filter");
  const note = hasText && hasFilters ? "Semantic text is embedded with OpenCLIP; structured conditions are passed to the query planner."
    : hasText ? "The query is embedded with OpenCLIP and matched by meaning."
    : "No semantic text: this query is answered entirely by the database indexes.";
  el.innerHTML = `<div class="parsed-head"><span class="parsed-title">Parsed query</span>${stratBadge(data.plan.strategy)}</div>
    <div class="qchips">${chipsHTML(chips)}</div><div class="parsed-note">${esc(note)}</div>`;
  el.classList.remove("hidden");
}

function renderResults(data) {
  state.lastData = data;
  state.results = data.results;
  const p = data.plan;
  renderParsed(data);
  $("#warnings").innerHTML = (p.warnings || []).map((w) => alertHTML(w, "warn")).join("");
  $("#strategy-indicator").innerHTML = `<button type="button" class="strategy-pill" data-route="plan" title="Open the execution plan">${icon("flow")}${esc(stratInfo(p.strategy).label)} · ${num(p.timings_ms.total, 1)} ms</button>`;
  const nf = state.pills.length;
  $("#filters-indicator").innerHTML = nf ? `<span class="pill accent">${nf} filter${nf === 1 ? "" : "s"}</span>` : "";
  renderGrid();
}

function renderGrid() {
  const data = state.lastData;
  if (!data) return;
  const hasScores = state.results.some((r) => r.cosine !== null && r.cosine !== undefined);
  const slider = $("#min-sim");
  slider.disabled = !hasScores;
  const minSim = hasScores ? Number(slider.value) : 0;
  let items = state.results.filter((r) => r.cosine === null || r.cosine === undefined || r.cosine >= minSim);
  const hidden = state.results.length - items.length;
  const sort = $("#sort").value;
  if (sort !== "relevance") {
    items = [...items].sort((a, b) => {
      const ta = a.taken_at || ""; const tb = b.taken_at || "";
      return sort === "newest" ? tb.localeCompare(ta) : ta.localeCompare(tb);
    });
  }
  $("#result-count").innerHTML = `<b>${items.length}</b> ${items.length === 1 ? "photo" : "photos"}${hidden ? ` <span class="muted">· ${hidden} below threshold</span>` : ""}`;
  $("#grid").innerHTML = items.map((r) => cardHTML(r, sort === "relevance")).join("");
  const empty = $("#empty");
  if (items.length) { empty.classList.add("hidden"); return; }
  empty.innerHTML = data.plan.n_vectors === 0 && data.plan.strategy !== "metadata_only"
    ? emptyState("upload", "Your library is empty", "Add photos on the Ingest page or run the dataset script.", '<button class="btn primary" data-route="ingest">Open ingest</button>')
    : emptyState("search", "No matching photos", "Try loosening the filters, lowering the similarity threshold or rephrasing.");
  empty.classList.remove("hidden");
}

function cardHTML(r, showRank = false) {
  const fav = favorites.has(r.id);
  const cam = [r.camera_make, r.camera_model].filter(Boolean).join(" ");
  const tags = (r.tags || []).filter((t) => t !== "synthetic-geo").slice(0, 3).map((t) => `<span class="tag">${esc(t)}</span>`).join("");
  const sim = r.cosine !== null && r.cosine !== undefined
    ? `<span class="score" title="cosine ${num(r.cosine, 4)} · fused score ${num(r.score, 4)}">${num(r.cosine, 2)}</span>` : "";
  return `<article class="photo" data-id="${r.id}" tabindex="0" title="${esc(r.caption || r.file_name)}">
    <div class="photo-img">
      <img loading="lazy" src="${esc(r.thumb_url)}" alt="${esc(r.caption || r.file_name)}">
      ${showRank && r.rank ? `<span class="rank">${r.rank}</span>` : ""}
      <button type="button" class="fav-btn ${fav ? "on" : ""}" data-fav="${r.id}" aria-label="Favorite">${icon("star")}</button>
    </div>
    <div class="photo-body">
      <div class="photo-meta"><span>${icon("calendar")}${esc(fmtDate(r.taken_at))}</span>${sim}</div>
      ${cam ? `<div class="photo-cam">${icon("camera")}${esc(cam)}</div>` : ""}
      <div class="photo-tags">${tags}</div>
    </div>
  </article>`;
}
function toggleFavorite(id) {
  if (favorites.has(id)) favorites.delete(id); else favorites.add(id);
  saveFavorites();
  const on = favorites.has(id);
  $$(`[data-fav="${id}"]`).forEach((b) => b.classList.toggle("on", on));
  if (state.current && state.current.id === id) $("#d-fav").classList.toggle("on", on);
  toast(on ? `Added #${id} to favorites` : `Removed #${id} from favorites`, "ok");
}
function wireGrid(el) {
  el.addEventListener("click", (e) => {
    const fav = e.target.closest("[data-fav]");
    if (fav) { toggleFavorite(Number(fav.dataset.fav)); return; }
    const card = e.target.closest(".photo");
    if (card) openInspector(Number(card.dataset.id));
  });
  el.addEventListener("keydown", (e) => {
    const card = e.target.closest(".photo");
    if (card && e.key === "Enter") openInspector(Number(card.dataset.id));
  });
}
wireGrid($("#grid"));
wireGrid($("#lib-grid"));

/* ---------------------------------------------------------------- library */
function libTitle(mode, value) {
  switch (mode) {
    case "favorites": return ["Favorites", "Photos you starred · stored in this browser"];
    case "recent": return ["Recent", "Most recently added photos"];
    case "places": return value ? [`Near ${fmtCoord(...value.split(",").map(Number))}`, "Photos within 60 km · R*Tree radius query"] : ["Places", "Geotagged photos grouped by location"];
    case "tag": return [value, "Collection · photos with this tag"];
    case "source": return [value, "Collection · photos from this source"];
    default: return ["All photos", "Every photo in your library"];
  }
}
async function openLibrary(mode, value = "", append = false) {
  const L = state.library;
  if (!append) Object.assign(L, { mode, value, offset: 0, total: 0, items: [] });
  const [title, sub] = libTitle(mode, value);
  setHeader(mode === "tag" || mode === "source" ? "Collections" : "Library", title);
  $("#lib-title").textContent = title;
  $("#lib-sub").textContent = sub;
  $("#lib-sort-wrap").classList.toggle("hidden", mode === "recent" || (mode === "places" && !!value));
  $("#places").classList.toggle("hidden", !(mode === "places" && !value));
  if (mode === "places" && !value) renderPlaces();
  if (!append) $("#lib-grid").innerHTML = '<div class="loading">Loading photos…</div>';
  try {
    let items; let total;
    if (mode === "places" && value) {
      const [lat, lon] = value.split(",").map(Number);
      const data = await jsonPost("/api/search", { q: "", k: 200, filters: { near_lat: lat, near_lon: lon, near_km: 60 } });
      items = data.results; total = items.length;
    } else if (mode === "favorites") {
      if (!favorites.size) { items = []; total = 0; }
      else {
        const qs = new URLSearchParams({ ids: [...favorites].slice(0, 200).join(","), limit: "200", sort: $("#lib-sort").value });
        const r = await api(`/api/photos?${qs}`); items = r.items; total = r.total;
      }
    } else {
      const qs = new URLSearchParams({ limit: "60", offset: String(L.offset), sort: mode === "recent" ? "ingested" : $("#lib-sort").value });
      if (mode === "tag") qs.set("tag", value);
      if (mode === "source") qs.set("source", value);
      if (mode === "places") qs.set("geotagged", "true");
      const r = await api(`/api/photos?${qs}`); items = r.items; total = r.total;
    }
    L.items = append ? L.items.concat(items) : items;
    L.total = total;
    L.offset = L.items.length;
    renderLibGrid();
  } catch (err) {
    $("#lib-grid").innerHTML = alertHTML(err.message);
  }
}
function renderLibGrid() {
  const L = state.library;
  const grid = $("#lib-grid");
  if (!L.items.length) {
    grid.innerHTML = L.mode === "favorites"
      ? emptyState("star", "No favorites yet", "Star photos in search results or the inspector to collect them here.")
      : emptyState("images", "No photos here", "Nothing matches this view yet.");
  } else {
    grid.innerHTML = L.items.map((r) => cardHTML(r)).join("");
  }
  const more = L.items.length < L.total && L.mode !== "favorites" && !(L.mode === "places" && L.value);
  $("#lib-more").classList.toggle("hidden", !more);
  $("#lib-more").textContent = more ? `Load more (${(L.total - L.items.length).toLocaleString()} remaining)` : "Load more";
  $("#lib-sub").textContent = `${libTitle(L.mode, L.value)[1]} · ${L.total.toLocaleString()} photo${L.total === 1 ? "" : "s"}`;
}
function renderPlaces() {
  const places = state.collections?.places || [];
  $("#places").innerHTML = places.length
    ? places.map((p) => `<button type="button" class="place-card" data-route="library:places:${p.lat},${p.lon}">
        <img src="${esc(p.cover)}" alt=""><div><div class="place-title">${esc(fmtCoord(p.lat, p.lon))}</div><div class="place-sub">${p.count} photo${p.count === 1 ? "" : "s"}</div></div></button>`).join("")
    : '<div class="muted">No geotagged photos yet. Ingest photos with GPS data, or use --synthetic-geo for the demo dataset.</div>';
}
$("#lib-sort").addEventListener("change", () => openLibrary(state.library.mode, state.library.value));
$("#lib-more").addEventListener("click", () => openLibrary(state.library.mode, state.library.value, true));

/* ---------------------------------------------------------------- inspector drawer */
const section = (title, ic, body, { open = true, extra = "" } = {}) =>
  `<details class="insp-sec" ${open ? "open" : ""}><summary>${icon("chevron", "chev")}${icon(ic)}<span>${esc(title)}</span>${extra ? `<span class="sec-extra">${extra}</span>` : ""}</summary><div class="sec-body">${body}</div></details>`;

async function openInspector(id) {
  let d;
  try { d = await api(`/api/photos/${id}`); } catch (err) { toast(err.message, "err"); return; }
  state.current = d;
  state.selectedObj = null;
  $("#d-title").textContent = d.caption || d.file_name;
  $("#d-sub").innerHTML = `<span class="pill">#${d.id}</span><span>${esc(d.file_name)}</span><span>·</span><span>${esc(fmtDate(d.taken_at))}</span><span>·</span><span>${esc(d.source)}</span>`;
  $("#d-fav").classList.toggle("on", favorites.has(d.id));
  $("#d-open").href = d.image_url;
  $("#d-delete").classList.toggle("hidden", state.readOnly);
  $("#d-dims").textContent = d.width ? `${d.width} × ${d.height}` : "";
  const img = $("#d-img");
  state.fitW = 0;
  img.onload = () => { if (state.zoom === 1) state.fitW = img.clientWidth; };
  img.src = d.image_url;
  img.alt = d.caption || d.file_name;
  setZoom(1);
  renderBoxes();
  renderObjectChips();
  renderInspectorInfo();
  $("#drawer").classList.remove("hidden");
  document.body.classList.add("drawer-open");
  loadSimilarInDrawer(d.id);
}
function renderBoxes() {
  const d = state.current;
  if (!d) return;
  const sel = state.selectedObj;
  $("#bbox-layer").innerHTML = (d.objects || []).map((o) =>
    `<div class="bbox ${sel === o.id ? "active" : sel ? "dim" : ""}" style="left:${o.x_min * 100}%;top:${o.y_min * 100}%;width:${(o.x_max - o.x_min) * 100}%;height:${(o.y_max - o.y_min) * 100}%"><span>${esc(o.label)}</span></div>`).join("");
  $("#bbox-layer").classList.toggle("hidden", !$("#toggle-boxes").checked);
}
function renderObjectChips() {
  const d = state.current;
  const objs = d?.objects || [];
  $("#d-objects").innerHTML = objs.length
    ? objs.map((o) => `<button type="button" class="obj-chip ${state.selectedObj === o.id ? "active" : ""}" data-obj="${o.id}">${esc(o.label)} <span class="dim">${num(o.score, 2)}</span></button>`).join("")
    : '<span class="dim small">No detected objects for this photo.</span>';
}
function selectObject(id) {
  state.selectedObj = state.selectedObj === id ? null : id;
  if (state.selectedObj && !$("#toggle-boxes").checked) $("#toggle-boxes").checked = true;
  renderBoxes();
  renderObjectChips();
  $$("#d-info tr[data-obj]").forEach((tr) => tr.classList.toggle("sel", Number(tr.dataset.obj) === state.selectedObj));
  const o = (state.current.objects || []).find((x) => x.id === state.selectedObj);
  const el = $("#sel-region");
  if (el) el.innerHTML = o ? `<span class="mono">${esc(o.label)}: x ${num(o.x_min, 3)}–${num(o.x_max, 3)}, y ${num(o.y_min, 3)}–${num(o.y_max, 3)}</span>` : '<span class="dim">Select an object to see its region</span>';
}
$("#d-objects").addEventListener("click", (e) => { const b = e.target.closest("[data-obj]"); if (b) selectObject(Number(b.dataset.obj)); });
$("#d-info").addEventListener("click", (e) => {
  const tr = e.target.closest("tr[data-obj]");
  if (tr) { selectObject(Number(tr.dataset.obj)); return; }
  const sim = e.target.closest("[data-sim]");
  if (sim) openInspector(Number(sim.dataset.sim));
});

function renderInspectorInfo() {
  const d = state.current;
  const s = state.stats;
  const exposure = d.exposure_time ? (d.exposure_time < 1 ? `1/${Math.round(1 / d.exposure_time)} s` : `${d.exposure_time} s`) : null;
  const hasGeo = d.gps_lat !== null && d.gps_lat !== undefined && d.gps_lon !== null && d.gps_lon !== undefined;
  const groups = {};
  (d.tags || []).forEach((t) => { (groups[t.origin] = groups[t.origin] || []).push(t); });
  const tagHTML = ["manual", "annotation", "clip"].filter((o) => groups[o]).map((origin) => `<div class="tag-group">
      <div class="tag-origin">${esc(ORIGIN_LABEL[origin])}</div>
      <div class="chips">${groups[origin].map((t) => `<span class="tag ${origin}">${esc(t.name)}${origin === "clip" ? `<em>${Math.round(t.confidence * 100)}%</em>` : ""}</span>`).join("")}</div>
    </div>`).join("") || '<div class="dim">No tags.</div>';
  const objRows = (d.objects || []).map((o) => {
    const area = (o.x_max - o.x_min) * (o.y_max - o.y_min) * 100;
    return `<tr data-obj="${o.id}"><td>${esc(o.label)}</td><td class="r mono">${num(o.score, 2)}</td><td class="mono">${num(o.x_min, 2)}, ${num(o.y_min, 2)} → ${num(o.x_max, 2)}, ${num(o.y_max, 2)}</td><td class="r mono">${area.toFixed(1)}%</td></tr>`;
  }).join("");

  $("#d-info").innerHTML = [
    section("General information", "info", `${d.caption ? `<div class="caption-text">${esc(d.caption)}</div>` : ""}${kv([
      ["File name", d.file_name], ["Format", d.format], ["Dimensions", d.width ? `${d.width} × ${d.height} px` : null],
      ["File size", bytes(d.file_size)], ["Source", d.source],
      ["Added", d.created_at ? d.created_at.replace("T", " ").slice(0, 19) : null],
      ["SHA-256", `<span class="mono">${esc(d.file_hash.slice(0, 20))}…</span>`, true],
    ])}`),
    section("EXIF metadata", "camera", kv([
      ["Date taken", d.taken_at ? d.taken_at.replace("T", " ") : null],
      ["Camera", [d.camera_make, d.camera_model].filter(Boolean).join(" ")], ["Lens", d.lens_model],
      ["Focal length", d.focal_length ? `${num(d.focal_length, 1)} mm` : null],
      ["Aperture", d.f_number ? `ƒ/${num(d.f_number, 1)}` : null], ["Exposure", exposure], ["ISO", d.iso],
    ])),
    section("AI-generated tags", "sparkles", tagHTML, { extra: `${(d.tags || []).length}` }),
    section("Detected objects", "box", objRows
      ? `<div class="table-wrap"><table class="table"><thead><tr><th>Label</th><th class="r">Score</th><th>Box (x₁, y₁ → x₂, y₂)</th><th class="r">Area</th></tr></thead><tbody>${objRows}</tbody></table></div>
         <p class="small muted" style="margin-top:8px">Click a row or a chip under the photo to highlight its bounding box.</p>`
      : '<div class="dim">No bounding boxes stored for this photo.</div>', { extra: `${(d.objects || []).length}` }),
    section("Spatial information", "pin", kv([
      ["GPS", hasGeo ? fmtCoord(d.gps_lat, d.gps_lon) : null],
      ["Map", hasGeo ? `<a href="https://www.openstreetmap.org/?mlat=${d.gps_lat}&mlon=${d.gps_lon}#map=13/${d.gps_lat}/${d.gps_lon}" target="_blank" rel="noopener">Open in OpenStreetMap</a>` : null, true],
      ["Geo index", hasGeo ? "geo_rtree (R*Tree point)" : "not geotagged"],
      ["Object index", (d.objects || []).length ? `object_rtree · ${(d.objects || []).length} boxes` : "no boxes"],
      ["Selected region", '<span id="sel-region"><span class="dim">Select an object to see its region</span></span>', true],
    ]), { open: false }),
    section("Embedding information", "cpu", kv([
      ["Model", s ? s.embedding.model_id : null], ["Dimensions", s ? s.embedding.dim : null],
      ["Similarity", "cosine (inner product of L2-normalised vectors)"],
      ["Vector index", d.has_embedding ? `FAISS HNSW${s ? ` · M=${s.vector_index.M}, efSearch=${s.vector_index.ef_search}` : ""}` : "not indexed"],
      ["Stored in", "SQLite photo_embeddings (float32 BLOB)"],
    ]), { open: false }),
    section("Similar photos", "layers", '<div class="sim-grid" id="d-sim"><span class="dim small">Loading…</span></div>'),
  ].join("");
}
async function loadSimilarInDrawer(id) {
  try {
    const data = await jsonPost("/api/similar", { photo_id: id, k: 6 });
    if (!state.current || state.current.id !== id) return;
    $("#d-sim").innerHTML = data.results.map((r) =>
      `<button type="button" class="sim-item" data-sim="${r.id}" title="#${r.id} · cosine ${num(r.cosine, 3)}"><img src="${esc(r.thumb_url)}" alt=""><span>${num(r.cosine, 2)}</span></button>`).join("")
      || '<span class="dim small">No neighbours found.</span>';
  } catch {
    const el = $("#d-sim"); if (el) el.innerHTML = '<span class="dim small">Unavailable.</span>';
  }
}
function setZoom(z) {
  const img = $("#d-img");
  state.zoom = Math.min(4, Math.max(1, z));
  if (state.zoom === 1) {
    img.style.width = ""; img.style.maxWidth = ""; img.style.maxHeight = "";
  } else {
    if (!state.fitW) state.fitW = img.clientWidth;
    img.style.maxWidth = "none"; img.style.maxHeight = "none";
    img.style.width = `${Math.round(state.fitW * state.zoom)}px`;
  }
  $("#zoom-val").textContent = `${Math.round(state.zoom * 100)}%`;
}
$("#zoom-in").addEventListener("click", () => setZoom(state.zoom + 0.5));
$("#zoom-out").addEventListener("click", () => setZoom(state.zoom - 0.5));
$("#zoom-fit").addEventListener("click", () => setZoom(1));
$("#toggle-boxes").addEventListener("change", renderBoxes);
function closeDrawer() {
  if ($("#drawer").classList.contains("hidden")) return;
  $("#drawer").classList.add("hidden");
  document.body.classList.remove("drawer-open");
  $("#d-img").removeAttribute("src");
  state.current = null;
}
$("#d-close").addEventListener("click", closeDrawer);
$("#drawer").addEventListener("click", (e) => { if (e.target.id === "drawer") closeDrawer(); });
$("#d-fav").addEventListener("click", () => { if (state.current) toggleFavorite(state.current.id); });
$("#d-similar").addEventListener("click", () => { if (state.current) findSimilar(state.current.id); });
$("#d-copy").addEventListener("click", async () => {
  if (!state.current) return;
  try { await navigator.clipboard.writeText(String(state.current.id)); toast(`Copied photo ID ${state.current.id}`, "ok"); }
  catch { toast("Clipboard is not available in this browser context", "err"); }
});
$("#d-delete").addEventListener("click", async () => {
  const d = state.current;
  if (!d || !window.confirm(`Delete photo #${d.id} (${d.file_name})? It is removed from SQLite and its vector is tombstoned.`)) return;
  try {
    await api(`/api/photos/${d.id}`, { method: "DELETE" });
    toast(`Deleted photo #${d.id}`, "ok");
    closeDrawer();
    $$(`.photo[data-id="${d.id}"]`).forEach((el) => el.remove());
    if (favorites.delete(d.id)) saveFavorites();
    loadStats(); loadCollections();
  } catch (err) { toast(err.message, "err"); }
});

/* ---------------------------------------------------------------- ingest */
const dz = $("#dropzone");
["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("over"); }));
dz.addEventListener("drop", (e) => addFiles(e.dataTransfer.files));
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("drop", (e) => e.preventDefault());
$("#file-input").addEventListener("change", (e) => { addFiles(e.target.files); e.target.value = ""; });
$("#queue-clear").addEventListener("click", () => { state.queue.forEach((q) => URL.revokeObjectURL(q.url)); state.queue = []; renderQueue(); });
$("#queue").addEventListener("click", (e) => {
  const b = e.target.closest("[data-remove]");
  if (!b) return;
  const i = state.queue.findIndex((q) => q.key === b.dataset.remove);
  if (i >= 0) { URL.revokeObjectURL(state.queue[i].url); state.queue.splice(i, 1); renderQueue(); }
});
function addFiles(list) {
  let skipped = 0;
  for (const f of list) {
    if (!f.type.startsWith("image/")) { skipped++; continue; }
    const key = `${f.name}|${f.size}|${f.lastModified}`;
    if (state.queue.some((q) => q.key === key)) continue;
    state.queue.push({ file: f, key, url: URL.createObjectURL(f) });
  }
  if (skipped) toast(`${skipped} non-image file${skipped > 1 ? "s" : ""} skipped`, "info");
  renderQueue();
}
function renderQueue() {
  const n = state.queue.length; const MAX = 60;
  $("#queue-head").classList.toggle("hidden", !n);
  $("#queue-count").textContent = `${n} file${n === 1 ? "" : "s"} ready · ${bytes(state.queue.reduce((a, q) => a + q.file.size, 0))}`;
  $("#queue").innerHTML = state.queue.slice(0, MAX).map((q) => `<div class="q-item"><img src="${q.url}" alt="">
      <div class="q-meta"><span title="${esc(q.file.name)}">${esc(q.file.name)}</span><small>${bytes(q.file.size)}</small></div>
      <button type="button" class="q-remove" data-remove="${esc(q.key)}" aria-label="Remove">${icon("x")}</button></div>`).join("")
    + (n > MAX ? `<div class="q-more">+${n - MAX} more</div>` : "");
  const btn = $("#upload-btn");
  btn.disabled = !n || state.readOnly;
  btn.textContent = state.readOnly ? "Uploads disabled (read-only)" : n ? `Upload ${n} photo${n === 1 ? "" : "s"}` : "Add photos to upload";
}
$("#upload-btn").addEventListener("click", async () => {
  if (!state.queue.length || state.readOnly) return;
  const items = state.queue.splice(0);
  renderQueue();
  const total = items.length; let done = 0;
  const local = { ok: 0, dup: 0, err: 0 };
  $("#upload-btn").disabled = true;
  $("#up-progress").classList.remove("hidden");
  const progress = () => {
    $("#up-bar").style.width = `${((done / total) * 100).toFixed(1)}%`;
    $("#up-label").textContent = done < total ? `Processing ${done} of ${total}…` : `Finished ${total} file${total === 1 ? "" : "s"}.`;
  };
  progress();
  for (let i = 0; i < total; i += 8) {
    const batch = items.slice(i, i + 8);
    const fd = new FormData();
    batch.forEach((q) => fd.append("files", q.file));
    fd.append("caption", $("#up-caption").value);
    fd.append("tags", $("#up-tags").value);
    fd.append("autotag", $("#up-autotag").checked ? "true" : "false");
    let rows;
    try { rows = (await api("/api/upload", { method: "POST", body: fd })).results; }
    catch (err) { rows = batch.map((q) => ({ file_name: q.file.name, status: "error", detail: err.message })); }
    rows.forEach((r) => { const k = r.status === "ingested" ? "ok" : r.status === "duplicate" ? "dup" : "err"; local[k]++; state.tallies[k]++; });
    logRows(rows);
    done += batch.length;
    progress();
  }
  items.forEach((q) => URL.revokeObjectURL(q.url));
  $("#t-ok").textContent = state.tallies.ok;
  $("#t-dup").textContent = state.tallies.dup;
  $("#t-err").textContent = state.tallies.err;
  renderQueue(); loadStats(); loadCollections();
  toast(`Completed ${local.ok}, duplicates ${local.dup}, errors ${local.err}`, local.err ? "err" : "ok");
});
function logRows(rows) {
  const tbody = $("#upload-log");
  tbody.querySelector(".empty-row")?.remove();
  tbody.insertAdjacentHTML("afterbegin", rows.map((r) => {
    const status = r.status === "ingested" ? '<span class="pill ok">Completed</span>' : r.status === "duplicate" ? '<span class="pill dup">Duplicate</span>' : '<span class="pill err">Error</span>';
    const details = r.status === "ingested" ? `${(r.tags || []).length} tags · ${(r.tags || []).slice(0, 4).join(", ")}`
      : r.status === "duplicate" ? `SHA-256 match${r.photo_id ? ` (photo #${r.photo_id})` : ""}${r.detail ? ` · ${r.detail}` : ""}`
      : r.detail || "Unknown error";
    return `<tr><td>${esc(r.file_name)}</td><td>${status}</td><td class="muted">${esc(details)}</td>
      <td>${r.photo_id ? `<button type="button" class="link" data-open="${r.photo_id}">#${r.photo_id}</button>` : '<span class="dim">—</span>'}</td></tr>`;
  }).join(""));
}

/* ---------------------------------------------------------------- execution plan */
function highlightSQL(sql) {
  return esc(sql)
    .replace(/\b(SELECT|FROM|WHERE|AND|OR|IN|JOIN|ON|ORDER BY|GROUP BY|LIMIT|MATCH|BETWEEN|AS|NOT|NULL|IS|DESC|ASC|COUNT|LIKE)\b/g, '<span class="kw">$1</span>')
    .replace(/\?/g, '<span class="ph">?</span>');
}
function indexesUsed(lines) {
  const out = new Set();
  (lines || []).forEach((raw) => {
    const l = raw.trim(); let m;
    if (/VIRTUAL TABLE INDEX/.test(l)) { m = /(?:SCAN|SEARCH) (\w+)/.exec(l); out.add(`${m ? m[1] : "virtual table"} · virtual-table index`); }
    else if ((m = /USING (?:COVERING )?INDEX (\w+)/.exec(l))) out.add(`${m[1]} · B-tree index`);
    else if (/USING INTEGER PRIMARY KEY/.test(l)) { m = /SEARCH (\w+)/.exec(l); out.add(`${m ? m[1] : "table"} · rowid lookup`); }
    else if ((m = /^SCAN (\w+)/.exec(l))) out.add(`${m[1]} · full scan`);
  });
  return [...out];
}
function candidatesOf(p) {
  const steps = p.steps || [];
  const ff = steps.find((s) => s.op.startsWith("SQL filter scan"));
  if (ff) return ff.rows;
  const h = [...steps].reverse().find((s) => s.op.startsWith("HNSW"));
  return h ? h.rows : null;
}
function flowNodes(entry) {
  const p = entry.plan; const t = p.timings_ms || {};
  const nodes = [{ title: "User query", io: true, body: chipsHTML(parsedChips(entry.query || {})) || esc(entry.label) }];
  if (t.encode) nodes.push({ title: "Encode query", bucket: "encode", ms: t.encode, detail: "OpenCLIP encoder → 512-d L2-normalised vector" });
  (p.steps || []).forEach((s) => nodes.push({ title: s.op, bucket: s.bucket, ms: s.ms, rows: s.rows, detail: s.detail }));
  nodes.push({ title: "Final results", io: true, rows: p.returned, body: `${p.returned} photos returned (k = ${p.k})` });
  return nodes;
}
function flowNodeHTML(n, p, total) {
  const color = n.io ? "var(--line-2)" : bucketColor(n.bucket);
  const metrics = [n.rows !== null && n.rows !== undefined ? `${Number(n.rows).toLocaleString()} rows` : "", n.ms !== undefined ? `${num(n.ms, 3)} ms` : ""].filter(Boolean).join(" · ");
  let body = n.body || "";
  if (!n.io) {
    const share = total ? (n.ms / total) * 100 : 0;
    body += kv([
      ["Engine", BUCKET_LABEL[n.bucket] || n.bucket],
      ["Execution time", `${num(n.ms, 3)} ms (${share.toFixed(1)}% of engine time)`],
      ["Output rows", n.rows !== null && n.rows !== undefined ? Number(n.rows).toLocaleString() : null],
      ["Detail", n.detail ? `<span class="mono">${esc(n.detail)}</span>` : null, true],
    ]);
    body += `<div class="fn-bar"><div style="width:${Math.max(1, share).toFixed(1)}%;background:${color}"></div></div>`;
    const lexSql = (p.sql || []).find((s) => s.includes("bm25"));
    const filterSql = (p.sql || []).find((s) => !s.includes("bm25"));
    if (n.title.startsWith("FTS5") && lexSql) body += `<div><div class="section-label">SQL</div><pre class="code">${highlightSQL(lexSql)}</pre></div>`;
    else if (n.bucket === "sqlite" && filterSql && !n.title.startsWith("fetch")) {
      const idx = indexesUsed(p.sqlite_query_plan);
      body += `<div><div class="section-label">SQL</div><pre class="code">${highlightSQL(filterSql)}</pre></div>`;
      if (idx.length) body += `<div><div class="section-label">Indexes used</div><div class="idx-list">${idx.map((i) => `<span class="pill accent">${esc(i)}</span>`).join("")}</div></div>`;
      if ((p.sqlite_query_plan || []).length) body += `<div><div class="section-label">EXPLAIN QUERY PLAN</div><pre class="code">${esc(p.sqlite_query_plan.join("\n"))}</pre></div>`;
    }
  }
  return `<div class="flow-node ${n.io ? "io" : ""}"><details ${n.io ? "open" : ""}>
    <summary><span class="fn-dot" style="background:${color}"></span><span class="fn-title">${esc(n.title)}</span>
      ${n.io ? "" : `<span class="fn-eng">${esc(BUCKET_LABEL[n.bucket] || n.bucket)}</span>`}
      <span class="fn-metrics">${metrics}</span>${n.io ? "" : icon("chevron", "chev")}</summary>
    <div class="fn-body">${body}</div></details></div>`;
}

function renderPlan() {
  const root = $("#plan-root");
  const entry = state.history[state.planIndex];
  if (!entry) {
    root.innerHTML = emptyState("flow", "No query executed yet", "Run a search; how the optimizer executed it will appear here.", '<button class="btn primary" data-route="search">Go to search</button>');
    return;
  }
  const p = entry.plan; const t = p.timings_ms || {}; const e = p.estimates; const s = stratInfo(p.strategy);
  const isLatest = state.planIndex === 0;
  const engineMs = (t.total || 0) - (t.encode || 0);
  const history = state.history.map((h, i) => `<option value="${i}" ${i === state.planIndex ? "selected" : ""}>${esc(fmtTime(h.at))} · ${esc(stratInfo(h.plan.strategy).label)} · ${esc(h.label)}</option>`).join("");
  const canRerun = isLatest && !!state.lastRun;

  const tiles = e ? [
    ["Filter-first estimate", `${num(e.filter_first_ms, 3)} ms`, p.strategy === "filter_first" ? "chosen" : "", `≈ ${num(e.estimated_rows, 0)} rows scored exactly`],
    ["Vector-first estimate", `${num(e.vector_first_ms, 3)} ms`, p.strategy === "vector_first" ? "chosen" : "", e.degenerate ? "degenerate: k′ too large" : `k′ = ${e.k_prime}, efSearch = ${e.ef_search}`],
    ["Estimated selectivity", pct(e.selectivity), "", "independence assumption"],
    ["Estimated candidates", Number(Math.round(e.estimated_rows)).toLocaleString(), "", `of ${Number(e.n_rows).toLocaleString()} photos`],
    ["Over-fetch k′", Number(e.k_prime).toLocaleString(), "", `k = ${p.k}, α = 1.5`],
    ["Vectors indexed", Number(p.n_vectors).toLocaleString(), "", "FAISS HNSW"],
  ] : [
    ["Results", String(p.returned), "", `k = ${p.k}`],
    ["Vectors indexed", Number(p.n_vectors).toLocaleString(), "", "FAISS HNSW"],
    ["Encode time", `${num(t.encode || 0, 2)} ms`, "", "OpenCLIP"],
    ["Engine time", `${num(engineMs, 3)} ms`, "", "planning + execution"],
    ["Predicates", String((p.predicates || []).length), "", "structured filters"],
    ["Lexical channel", p.lexical_query ? "on" : "off", "", p.lexical_query ? esc(p.lexical_query) : "no free text"],
  ];

  const buckets = BUCKETS.map(([k, label]) => ({ k, label, ms: t[k] || 0 }));
  const sum = buckets.reduce((a, b) => a + b.ms, 0) || 1;
  const nodes = flowNodes(entry);
  const totalSteps = (p.steps || []).reduce((a, x) => a + x.ms, 0) + (t.encode || 0);

  root.innerHTML = `
    <div class="plan-toolbar">
      <label class="tb-field">Plan <select id="plan-history">${history}</select></label>
      <div class="toolbar-right">
        <span class="muted small">Re-run this query as</span>
        <div class="seg" id="rerun-seg">
          ${["auto", "filter_first", "vector_first"].map((m) => `<button type="button" class="seg-btn ${p.mode_requested === m ? "active" : ""}" data-rerun="${m}" ${canRerun ? "" : "disabled"}>${m === "auto" ? "Auto" : stratInfo(m).label}</button>`).join("")}
        </div>
      </div>
    </div>

    <div class="card">
      <div class="section-label">A · Query summary</div>
      <div class="qchips">${chipsHTML(parsedChips(entry.query || {})) || `<span class="muted">${esc(entry.label)}</span>`}</div>
      <p class="parsed-note">${p.lexical_query ? `Lexical channel (FTS5 BM25): <code>${esc(p.lexical_query)}</code> · weight ${p.lexical_weight}` : "No lexical channel for this query."}</p>
      ${(p.warnings || []).map((w) => alertHTML(w, "warn")).join("")}
    </div>

    <div class="card strategy-card">
      <div class="strategy-main">
        <div class="section-label">B · Selected strategy</div>
        <div class="strategy-name ${s.cls}">${esc(s.label)}</div>
        <div class="big-ms">${num(engineMs, 3)} <small>ms engine · ${num(t.total, 2)} ms end-to-end</small></div>
        <div class="reason">${esc(p.reason)}</div>
        ${p.strategy_fallback ? '<p style="margin-top:8px"><span class="pill warn">Fell back to filter-first</span></p>' : ""}
      </div>
      <div class="tile-grid">${tiles.map(([l, v, c, sub]) => `<div class="tile ${c}"><div class="tile-label">${esc(l)}</div><div class="tile-value">${v}</div><div class="tile-sub">${sub}</div></div>`).join("")}</div>
    </div>

    <div class="card">
      <div class="card-head"><h3>Where the time went</h3><span class="muted small">SQLite ${num(t.sqlite || 0, 3)} ms · FAISS ${num(t.faiss || 0, 3)} ms · exact ${num(t.exact || 0, 3)} ms</span></div>
      <div class="stack">${buckets.filter((b) => b.ms > 0).map((b) => `<div class="stack-seg" style="width:${((b.ms / sum) * 100).toFixed(2)}%;background:${bucketColor(b.k)}" title="${esc(b.label)}: ${num(b.ms, 3)} ms"></div>`).join("")}</div>
      <div class="legend">${buckets.map((b) => `<div class="legend-row"><span class="swatch" style="background:${bucketColor(b.k)}"></span><span>${esc(b.label)}</span><span class="mono">${num(b.ms, 3)} ms</span><span class="mono dim">${((b.ms / sum) * 100).toFixed(1)}%</span></div>`).join("")}</div>
    </div>

    <div class="two-col">
      <div class="card">
        <div class="card-head"><h3>C · Execution flow</h3><span class="muted small">Click an operator for details</span></div>
        <div class="flow">${nodes.map((n) => flowNodeHTML(n, p, totalSteps)).join("")}</div>
      </div>
      <div>
        <div class="card">
          <div class="card-head"><h3>Selectivity estimation</h3></div>
          ${(p.predicates || []).length ? `<div class="table-wrap"><table class="table"><thead><tr><th>Predicate</th><th>Estimator</th><th class="r">Selectivity</th><th class="r">Rows</th></tr></thead><tbody>
            ${p.predicates.map((r) => `<tr><td class="mono">${esc(r.predicate)}</td><td class="muted">${esc(r.method)}</td><td class="r mono">${pct(r.selectivity)}</td><td class="r mono">${num(r.estimated_rows, 0)}</td></tr>`).join("")}</tbody></table></div>`
            : '<p class="muted">No structured predicates in this query.</p>'}
          ${e ? `<pre class="code" style="margin-top:14px">${esc(e.formula.filter_first)}\n${esc(e.formula.vector_first)}</pre>` : ""}
        </div>
        ${(p.vector_first_attempts || []).length ? `<div class="card"><div class="card-head"><h3>Vector-first adaptive over-fetch</h3></div>
          <div class="table-wrap"><table class="table"><thead><tr><th>Attempt</th><th class="r">k′</th><th class="r">HNSW returned</th><th class="r">Passed filters</th></tr></thead><tbody>
          ${p.vector_first_attempts.map((a) => `<tr><td>${a.attempt}</td><td class="r mono">${a.k_prime}</td><td class="r mono">${a.hnsw_returned}</td><td class="r mono">${a.survivors}</td></tr>`).join("")}</tbody></table></div></div>` : ""}
      </div>
    </div>

    <div class="card">
      <div class="card-head"><div><h3>D · Strategy comparison</h3><p class="muted small">Runs this exact query under each strategy (median of 3). Recall is measured against exact filter-first search.</p></div>
        <button type="button" class="btn primary" id="run-compare" ${isLatest && state.lastRun && !["metadata_only", "empty"].includes(p.strategy) ? "" : "disabled"}>${icon("compare")}Run comparison</button></div>
      <div id="compare-out">${isLatest && state.compare ? state.compare : '<p class="muted">Not run yet. Available for the latest vector-based query.</p>'}</div>
    </div>`;

  $("#plan-history").addEventListener("change", (ev) => { state.planIndex = Number(ev.target.value); renderPlan(); });
  $$("#rerun-seg [data-rerun]").forEach((b) => b.addEventListener("click", () => rerun(b.dataset.rerun)));
  $("#run-compare")?.addEventListener("click", runCompare);
}

async function rerun(mode) {
  const run = state.lastRun;
  if (!run) return;
  try {
    const data = await run.run(mode);
    pushHistory(`${run.label.replace(/ \(forced.*\)$/, "")}${mode === "auto" ? "" : ` (forced ${stratInfo(mode).label.toLowerCase()})`}`, data);
    renderResults(data);
    renderPlan();
    toast(`Re-ran as ${mode === "auto" ? "Auto" : stratInfo(mode).label}: ${num(data.plan.timings_ms.total, 2)} ms`, "ok");
  } catch (err) { toast(err.message, "err"); }
}

async function runCompare() {
  const run = state.lastRun; const btn = $("#run-compare"); const out = $("#compare-out");
  if (!run) return;
  btn.disabled = true;
  out.innerHTML = '<p class="muted">Running 9 queries…</p>';
  try {
    const cols = [];
    for (const mode of ["filter_first", "vector_first", "auto"]) {
      const lat = []; let last;
      for (let i = 0; i < 3; i++) {
        last = await run.run(mode);
        lat.push(last.plan.timings_ms.total - (last.plan.timings_ms.encode || 0));
      }
      lat.sort((a, b) => a - b);
      cols.push({ mode, plan: last.plan, ms: lat[1], ids: last.results.map((r) => r.id) });
    }
    const truth = new Set(cols[0].ids);
    const recall = (c) => (truth.size ? c.ids.filter((i) => truth.has(i)).length / truth.size : 1);
    const best = Math.min(cols[0].ms, cols[1].ms);
    const fastest = cols.reduce((a, c) => (c.ms < a.ms ? c : a), cols[0]);
    const rows = [
      ["Executed strategy", (c) => stratBadge(c.plan.strategy), false],
      ["Latency (engine, median of 3)", (c) => `${num(c.ms, 3)} ms`, true],
      ["Candidates examined", (c) => { const v = candidatesOf(c.plan); return v === null ? "—" : Number(v).toLocaleString(); }, false],
      ["Results returned", (c) => String(c.ids.length), false],
      [`Recall@${run ? settings.k : ""} vs exact`, (c) => `${(recall(c) * 100).toFixed(0)}%`, false],
      ["SQLite time", (c) => `${num(c.plan.timings_ms.sqlite, 3)} ms`, false],
      ["FAISS time", (c) => `${num(c.plan.timings_ms.faiss, 3)} ms`, false],
      ["Exact rerank time", (c) => `${num(c.plan.timings_ms.exact, 3)} ms`, false],
    ];
    const html = `<div class="table-wrap"><table class="table"><thead><tr><th>Metric</th><th>Filter-first (forced)</th><th>Vector-first (forced)</th><th>Auto (planner)</th></tr></thead><tbody>
      ${rows.map(([label, fn, mark]) => `<tr><td class="muted">${esc(label)}</td>${cols.map((c) => `<td class="${mark && c === fastest ? "best" : ""}">${fn(c)}</td>`).join("")}</tr>`).join("")}
      </tbody></table></div>
      <div class="compare-foot">Planner regret: <b>${num(cols[2].ms / Math.max(best, 1e-6), 2)}×</b> (auto ÷ fastest forced strategy). Values near 1.00× mean the optimizer chose the right plan.</div>`;
    state.compare = html;
    out.innerHTML = html;
  } catch (err) {
    out.innerHTML = alertHTML(err.message);
  } finally {
    btn.disabled = false;
  }
}

/* ---------------------------------------------------------------- system overview */
function latencyChart(recent, p95) {
  if (!recent.length) return '<p class="muted">No searches yet. Run a few queries to populate live latency telemetry.</p>';
  const W = 600; const H = 180;
  const max = Math.max(...recent.map((r) => r.ms), p95 || 0) * 1.12 || 1;
  const bw = W / recent.length;
  const bars = recent.map((r, i) => {
    const h = Math.max(1.5, (r.ms / max) * (H - 8));
    const cls = stratInfo(r.strategy).cls;
    return `<rect class="bar ${cls}" x="${(i * bw + bw * 0.15).toFixed(2)}" y="${(H - h).toFixed(2)}" width="${(bw * 0.7).toFixed(2)}" height="${h.toFixed(2)}"><title>${esc(stratInfo(r.strategy).label)} · ${num(r.ms, 2)} ms · ${esc(r.kind)}</title></rect>`;
  }).join("");
  const y95 = p95 ? H - (p95 / max) * (H - 8) : null;
  return `<div class="chart-wrap"><div class="chart-axis"><span>${num(max, 0)} ms</span><span>${num(max / 2, 0)}</span><span>0</span></div>
    <svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${bars}${y95 !== null ? `<line class="p95" x1="0" x2="${W}" y1="${y95}" y2="${y95}"/>` : ""}</svg></div>
    <div class="chart-legend"><span><i style="background:var(--teal)"></i>Filter-first</span><span><i style="background:var(--accent)"></i>Vector-first / only</span><span><i style="background:var(--slate)"></i>Metadata-only</span>${p95 ? '<span><i style="background:var(--amber)"></i>p95</span>' : ""}</div>`;
}
async function loadSystem() {
  const root = $("#system-root");
  if (!root.innerHTML) root.innerHTML = '<div class="loading">Loading telemetry…</div>';
  const s = await loadStats();
  if (!s) { root.innerHTML = alertHTML("Could not reach the engine."); return; }
  const L = s.library; const V = s.vector_index; const S = s.storage; const T = s.telemetry; const E = s.embedding; const caps = S.capabilities;
  const yes = (b) => (b ? '<span class="pill ok">available</span>' : '<span class="pill err">missing</span>');
  const fmtConst = (v) => (typeof v === "number" ? (v !== 0 && Math.abs(v) < 0.001 ? v.toExponential(3) : String(+v.toFixed(5))) : String(v));
  const maxTag = Math.max(1, ...s.top_tags.map((t) => t.count));
  const srcMax = Math.max(1, ...Object.values(L.sources));
  const metric = (ic, label, value, sub) => `<div class="metric"><div class="metric-head">${icon(ic)}${esc(label)}</div><div class="metric-value">${value}</div><div class="metric-sub">${sub}</div></div>`;
  const hs = (ic, cls, title, value) => `<div class="hs-item ${cls}">${icon(ic)}<div><div class="hs-title">${esc(title)}</div><div class="hs-value">${value}</div></div></div>`;
  const actions = [
    ["calibrate", "Recalibrate cost model", "Re-run micro-benchmarks for the BLAS, SQLite and HNSW cost constants.", "/api/admin/calibrate", false],
    ["reload", "Reload index from SQLite", "Pick up photos ingested by scripts while the server was running.", "/api/admin/reload", false],
    ["rebuild", "Rebuild HNSW index", "Purge tombstoned (deleted) vectors and rebuild the graph.", "/api/admin/rebuild-index", true],
  ];

  root.innerHTML = `
    <div class="card health-strip">
      ${hs("pulse", "ok", "Engine status", "Healthy")}
      ${hs(s.health.index_consistent ? "check" : "alert", s.health.index_consistent ? "ok" : "warn", "Index consistency", s.health.index_consistent ? "SQLite and FAISS in sync" : `${V.active} vectors vs ${s.health.model_embeddings} embeddings`)}
      ${hs("clock", "", "Uptime", fmtDuration(T.uptime_s))}
      ${hs("shield", "", "Access", s.server.read_only ? "Read-only demo" : s.server.token_protected ? "Token protected" : "Open (local)")}
    </div>
    <div class="metric-grid">
      ${metric("images", "Indexed photos", L.photos.toLocaleString(), `${L.tags.toLocaleString()} tags · ${L.objects.toLocaleString()} objects`)}
      ${metric("database", "Source of truth", "SQLite", `v${esc(caps.sqlite_version)} · ${esc(String(S.journal_mode).toUpperCase())}`)}
      ${metric("layers", "Vector index", "HNSW", `${V.ntotal.toLocaleString()} vectors · M=${V.M}, ef=${V.ef_search}`)}
      ${metric("cpu", "Embedding model", esc(modelShort(E.model_id)), `${E.dim}-d · ${esc(String(E.device).toUpperCase())}`)}
      ${metric("folder", "Storage", bytes((S.images_bytes || 0) + (S.thumbs_bytes || 0)), `images + thumbnails · ${(S.image_files || 0).toLocaleString()} files`)}
      ${metric("gauge", "Latency (p50)", T.p50_ms !== null ? `${num(T.p50_ms, 1)} ms` : "—", T.p95_ms !== null ? `p95 ${num(T.p95_ms, 1)} ms · ${T.searches} searches` : "no searches yet")}
    </div>
    <div class="two-col">
      <div class="card"><div class="card-head"><h3>Search latency</h3><span class="muted small">Last ${T.recent.length} queries, end-to-end</span></div>${latencyChart(T.recent, T.p95_ms)}</div>
      <div class="card"><div class="card-head"><h3>Ingestion statistics</h3></div>${kv([
        ["Photos", L.photos.toLocaleString()], ["Embeddings", L.embeddings.toLocaleString()],
        ["Tag assignments", L.tag_assignments.toLocaleString()], ["Object boxes", L.objects.toLocaleString()],
        ["Geotagged", L.geotagged.toLocaleString()],
        ["Date range", L.date_min ? `${L.date_min.slice(0, 10)} → ${(L.date_max || "").slice(0, 10)}` : null],
      ])}<div style="margin-top:14px">${Object.entries(L.sources).map(([k, v]) => `<div class="hbar"><span>${esc(k)}</span><div class="track-bar"><div class="fill" style="width:${((v / srcMax) * 100).toFixed(1)}%"></div></div><span class="mono">${v}</span></div>`).join("")}</div></div>
    </div>
    <div class="two-col">
      <div class="card"><div class="card-head"><h3>SQLite database</h3></div>${kv([
        ["Version", caps.sqlite_version], ["Journal mode", String(S.journal_mode).toUpperCase()],
        ["Database size", bytes(S.db_bytes)], ["WAL size", bytes(S.wal_bytes)],
        ["FTS5", yes(caps.fts5), true], ["R*Tree", yes(caps.rtree), true], ["JSON1", yes(caps.json1), true],
        ["Migrations", S.migrations.map((m) => `v${m.version} ${m.name}`).join(" · ")],
      ])}</div>
      <div class="card"><div class="card-head"><h3>FAISS index</h3></div>${kv([
        ["Type", V.type], ["Metric", V.metric], ["Dimensions", V.dim],
        ["Vectors (total / active)", `${V.ntotal.toLocaleString()} / ${V.active.toLocaleString()}`], ["Tombstones", V.tombstones],
        ["Parameters", `M = ${V.M} · efConstruction = ${V.ef_construction} · efSearch = ${V.ef_search}`],
        ["Index file", bytes(V.index_file_bytes)], ["RAM (estimated)", bytes(V.ram_bytes_estimate)],
      ])}</div>
    </div>
    <div class="two-col">
      <div class="card"><div class="card-head"><h3>Planner cost model</h3>${s.planner.calibrated ? '<span class="pill ok">calibrated on this machine</span>' : '<span class="pill">defaults</span>'}</div>
        <div class="table-wrap"><table class="table"><thead><tr><th>Constant</th><th>Meaning</th><th class="r">Value</th></tr></thead><tbody>
        ${Object.entries(s.planner).filter(([k]) => k !== "calibrated").map(([k, v]) => `<tr><td class="mono">${esc(k)}</td><td class="muted">${esc(COST_DOC[k] || "")}</td><td class="r mono">${esc(fmtConst(v))}</td></tr>`).join("")}
        </tbody></table></div></div>
      <div>
        <div class="card"><div class="card-head"><h3>Maintenance</h3>${s.server.read_only ? '<span class="pill warn">read-only</span>' : ""}</div>
          ${actions.map(([id, title, text, , write]) => `<div class="action-row"><div><div class="action-title">${esc(title)}</div><div class="action-text">${esc(text)}</div></div>
            <button type="button" class="btn" data-admin="${id}" ${write && s.server.read_only ? "disabled" : ""}>${icon("refresh")}Run</button></div>`).join("")}
        </div>
        <div class="card"><div class="card-head"><h3>Top tags</h3></div>
          ${s.top_tags.slice(0, 10).map((t) => `<div class="hbar"><span>${esc(t.name)}</span><div class="track-bar"><div class="fill" style="width:${((t.count / maxTag) * 100).toFixed(1)}%"></div></div><span class="mono">${t.count}</span></div>`).join("") || '<p class="muted">No tags yet.</p>'}
        </div>
      </div>
    </div>`;

  $$("[data-admin]", root).forEach((b) => b.addEventListener("click", async () => {
    const action = actions.find((a) => a[0] === b.dataset.admin);
    b.disabled = true;
    try {
      const res = await api(action[3], { method: "POST" });
      const summary = action[0] === "rebuild" ? `removed ${res.removed}, ${res.vectors} vectors`
        : action[0] === "reload" ? `${res.vectors} vectors loaded` : "constants updated";
      toast(`${action[1]}: ${summary}`, "ok");
      loadSystem(); loadCollections();
    } catch (err) { toast(err.message, "err"); b.disabled = false; }
  }));
}

/* ---------------------------------------------------------------- settings */
function renderSettings() {
  $("#set-k").value = String(settings.k);
  $("#set-lexw").value = String(settings.lexw);
  $("#set-mode").value = settings.mode;
  $("#set-fav-sub").textContent = `${favorites.size} photo${favorites.size === 1 ? "" : "s"} starred`;
  $("#set-hist-sub").textContent = `${state.history.length} plan${state.history.length === 1 ? "" : "s"} recorded this session`;
  const s = state.stats;
  $("#set-server").innerHTML = s ? kv([
    ["Embedding model", s.embedding.model_id], ["Device", String(s.embedding.device).toUpperCase()],
    ["Access", s.server.read_only ? "Read-only demo mode" : "Read and write"],
    ["Token gate", s.server.token_protected ? "Enabled" : "Off (local use)"],
    ["API docs", '<a href="/api/docs" target="_blank" rel="noopener">/api/docs</a>', true],
  ]) : '<p class="muted">Server information unavailable.</p>';
  applyTheme(); applyDensity();
}
$("#set-k").addEventListener("change", (e) => { settings.k = Number(e.target.value); saveSettings(); toast(`Results per query set to ${settings.k}`, "ok"); });
$("#set-lexw").addEventListener("change", (e) => { settings.lexw = Math.min(1, Math.max(0, Number(e.target.value) || 0)); e.target.value = settings.lexw; saveSettings(); });
$("#set-mode").addEventListener("change", (e) => { settings.mode = e.target.value; saveSettings(); toast(`Default strategy: ${e.target.selectedOptions[0].textContent}`, "ok"); });
$("#set-clear-fav").addEventListener("click", () => { favorites.clear(); saveFavorites(); $$(".fav-btn.on").forEach((b) => b.classList.remove("on")); renderSettings(); toast("Favorites cleared", "ok"); });
$("#set-clear-hist").addEventListener("click", () => { state.history = []; state.planIndex = 0; state.compare = null; $("#nav-plan-pill").classList.add("hidden"); renderSettings(); toast("Plan history cleared", "ok"); });

/* ---------------------------------------------------------------- boot */
hydrateIcons();
applyTheme();
applyDensity();
renderExamples();
renderRegionPresets();
renderRegion();
renderActiveFilters();
renderQueue();
updateFavCount();
go("search");
loadStats();
loadCollections();
runSearch();