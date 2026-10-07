"use strict";
/*
  Dashboard script. It contains NO metric definitions: the SQL files in sql/dashboard/ calculate
  the building blocks (counts and sums per day / hour) and export them as JSON. This script only
  filters those rows by queue and date, adds them up, divides once, and draws the result.
*/

const TARGET = 80;                                   // 80/20 service-level target, in percent
const DOCS_URL = "https://github.com/yllbesimi-sys/wfm-sql-dashboard/blob/main/docs/LEARNING.md";
const FILES = ["01_kpi_daily", "02_forecast_vs_actual_daily", "03_service_level_heatmap", "04_staffing_gap_hourly"];
const DAY_NAMES = ["", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const nf = new Intl.NumberFormat("en-US");
const hh = (h) => String(h).padStart(2, "0") + ":00";
const date = (iso, opts) => new Date(iso + "T12:00:00").toLocaleDateString("en-GB", opts);
const fmtDate = (iso) => date(iso, { day: "numeric", month: "short", year: "numeric" });
const signed = (v, d = 1) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(d);
const mmss = (s) => { const t = Math.round(s); return Math.floor(t / 60) + ":" + String(t % 60).padStart(2, "0"); };
const sum = (rows, key) => rows.reduce((t, r) => t + r[key], 0);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

let D = {};                                          // loaded datasets, as arrays of objects
let queues = [];
const state = { queue: "all", from: "", to: "" };
let forecastChart, staffChart, staffRows = [];

/* ---------- load ---------- */
async function load() {
  const parts = await Promise.all(FILES.map(async (name) => {
    const res = await fetch(`data/${name}.json`);
    if (!res.ok) throw new Error(`${name}.json: HTTP ${res.status}`);
    const j = await res.json();
    j.objs = j.rows.map((r) => Object.fromEntries(j.columns.map((c, i) => [c, r[i]])));
    return [name, j];
  }));
  return Object.fromEntries(parts);
}

/* ---------- filtering ---------- */
const selected = (rows) => rows.filter((r) =>
  (state.queue === "all" || r.queue === state.queue) && r.date >= state.from && r.date <= state.to);
const nQueues = () => (state.queue === "all" ? queues.length : 1);

/* ---------- heatmap colours: diverging around the 80% target ---------- */
const NEUTRAL = [240, 239, 236], BLUE = [28, 92, 171], RED = [179, 38, 43];
const mix = (a, b, t) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
function heatRgb(v) {
  return v >= TARGET
    ? mix(NEUTRAL, BLUE, Math.min(1, (v - TARGET) / (100 - TARGET)))
    : mix(NEUTRAL, RED, Math.min(1, (TARGET - v) / (TARGET - 40)));
}
function inkFor(rgb) {                               // black or white, whichever contrasts more
  const lin = (c) => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const L = 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2]);
  return (L + 0.05) / 0.05 >= 1.05 / (L + 0.05) ? "#000" : "#fff";
}

/* ---------- KPI band ---------- */
function renderKpis(rows, staffing) {
  const off = sum(rows, "offered");
  const ok = off > 0;
  const sl = ok ? (100 * sum(rows, "answered_within_20s")) / off : null;
  $("k-sl").textContent = ok ? sl.toFixed(1) : "–";
  $("k-offered").textContent = ok ? nf.format(off) : "–";
  $("k-abandon").textContent = ok ? ((100 * sum(rows, "abandoned")) / off).toFixed(1) + "%" : "–";
  $("k-aht").textContent = ok ? mmss(sum(rows, "handle_seconds") / sum(rows, "answered")) : "–";
  $("k-wape").textContent = ok ? ((100 * sum(rows, "abs_forecast_error")) / off).toFixed(1) + "%" : "–";
  const n = sum(staffing, "intervals");
  $("k-short").textContent = n ? ((100 * sum(staffing, "short_intervals")) / n).toFixed(0) + "%" : "–";

  const verdict = $("k-sl-verdict"), meter = $("k-sl-meter");
  verdict.replaceChildren();
  if (!ok) { $("k-sl-fill").style.width = "0"; return; }
  const diff = sl - TARGET;
  const text = Math.abs(diff) < 0.05 ? "On target"
    : diff > 0 ? `${diff.toFixed(1)} points above target` : `${(-diff).toFixed(1)} points below target`;
  verdict.append(el("span", "mark", Math.abs(diff) < 0.05 ? "=" : diff > 0 ? "▲" : "▼"), text);
  meter.classList.toggle("below", diff < 0);
  $("k-sl-fill").style.width = Math.min(100, sl) + "%";
  meter.setAttribute("aria-label", `Service level ${sl.toFixed(1)} percent against the ${TARGET} percent target`);
}

/* ---------- forecast vs actual ---------- */
function renderForecast(rows) {
  const byDate = new Map();
  for (const r of rows) {
    const a = byDate.get(r.date) || { f: 0, o: 0 };
    a.f += r.forecast_offered; a.o += r.offered;
    byDate.set(r.date, a);
  }
  const days = [...byDate.keys()].sort();
  forecastChart.data.labels = days;
  forecastChart.data.datasets[0].data = days.map((d) => byDate.get(d).o);
  forecastChart.data.datasets[1].data = days.map((d) => byDate.get(d).f);
  forecastChart.update("none");
  if (days.length) {
    $("c-forecast").setAttribute("aria-label",
      `Line chart of daily forecast and actual contacts, ${fmtDate(days[0])} to ${fmtDate(days[days.length - 1])}. A table view is available below.`);
  }
  $("table-forecast").replaceChildren(makeTable(
    ["Date", "Forecast", "Actual offered", "Difference"],
    days.map((d) => { const a = byDate.get(d); return [date(d, { weekday: "short", day: "numeric", month: "short" }), nf.format(a.f), nf.format(a.o), signed(a.o - a.f, 0)]; })));
}

/* ---------- heatmap ---------- */
function renderHeat(rows) {
  const cells = new Map();
  for (const r of rows) {
    const k = r.weekday * 100 + r.hour;
    const a = cells.get(k) || { off: 0, ok: 0 };
    a.off += r.offered; a.ok += r.answered_within_20s;
    cells.set(k, a);
  }
  const table = $("heat");
  const head = el("tr"); head.append(el("th"));
  for (let d = 1; d <= 6; d++) { const th = el("th", null, DAY_NAMES[d].slice(0, 3)); th.scope = "col"; th.title = DAY_NAMES[d]; head.append(th); }
  const thead = el("thead"); thead.append(head);
  const tbody = el("tbody");
  let weakest = null;
  for (const h of HOURS) {
    const tr = el("tr");
    const th = el("th", null, hh(h)); th.scope = "row"; tr.append(th);
    for (let d = 1; d <= 6; d++) {
      const a = cells.get(d * 100 + h);
      const td = el("td");
      if (!a || a.off === 0) { td.className = "empty"; td.textContent = "–"; tr.append(td); continue; }
      const v = (100 * a.ok) / a.off, rgb = heatRgb(v);
      td.textContent = String(Math.round(v));
      td.style.background = `rgb(${rgb})`; td.style.color = inkFor(rgb);
      td.tabIndex = 0;
      td.setAttribute("aria-label", `${DAY_NAMES[d]} ${hh(h)}, service level ${v.toFixed(1)} percent, ${nf.format(a.off)} contacts`);
      const tip = [`${v.toFixed(1)}%`, `${DAY_NAMES[d]} ${hh(h)} to ${String(h).padStart(2, "0")}:59`,
        `${nf.format(a.ok)} of ${nf.format(a.off)} contacts answered within 20 seconds`];
      td.addEventListener("pointerenter", () => showTip(td, tip));
      td.addEventListener("focus", () => showTip(td, tip));
      td.addEventListener("pointerleave", hideTip);
      td.addEventListener("blur", hideTip);
      if (a.off >= 30 && (!weakest || v < weakest.v)) weakest = { v, d, h, off: a.off };
      tr.append(td);
    }
    tbody.append(tr);
  }
  table.replaceChildren(thead, tbody);
  $("s-heat").textContent = "Percent of contacts answered within 20 seconds. " + (weakest
    ? `Weakest slot: ${DAY_NAMES[weakest.d]} ${hh(weakest.h)} at ${weakest.v.toFixed(1)}%.`
    : "Not enough contacts in this selection to name a weakest slot.");
}

/* ---------- staffing gap ---------- */
function renderStaffing(rows) {
  const byHour = new Map();
  for (const r of rows) {
    const a = byHour.get(r.hour) || { sched: 0, need: 0, n: 0, short: 0 };
    a.sched += r.scheduled_agent_intervals; a.need += r.needed_agent_intervals; a.n += r.intervals; a.short += r.short_intervals;
    byHour.set(r.hour, a);
  }
  staffRows = HOURS.filter((h) => byHour.has(h)).map((h) => {
    const a = byHour.get(h), slots = a.n / nQueues();          // half-hours, queues added together
    return { hour: h, sched: a.sched / slots, need: a.need / slots, gap: (a.sched - a.need) / slots, shortShare: (100 * a.short) / a.n };
  });
  staffChart.data.labels = staffRows.map((r) => hh(r.hour));
  staffChart.data.datasets[0].data = staffRows.map((r) => r.gap);
  staffChart.data.datasets[0].backgroundColor = staffRows.map((r) => (r.gap < 0 ? css("--red") : css("--blue")));
  staffChart.update("none");
  const worst = staffRows.reduce((m, r) => (!m || r.gap < m.gap ? r : m), null);
  $("s-staff").textContent = "Average agents scheduled minus agents needed, per half-hour. " + (worst && worst.gap < 0
    ? `Largest shortfall: ${hh(worst.hour)}, ${Math.abs(worst.gap).toFixed(1)} agents short.`
    : "No hour is short on average.");
  $("c-staff").setAttribute("aria-label", "Bar chart of the average staffing gap by hour. A table view is available below.");
  $("table-staff").replaceChildren(makeTable(
    ["Hour", "Scheduled", "Needed", "Gap", "Half-hours short"],
    staffRows.map((r) => [hh(r.hour), r.sched.toFixed(1), r.need.toFixed(1), signed(r.gap), r.shortShare.toFixed(0) + "%"])));
}

/* ---------- small helpers: tables, tooltip, SQL panels ---------- */
function makeTable(headers, rows) {
  const t = el("table"), thead = el("thead"), hr = el("tr");
  for (const h of headers) { const th = el("th", null, h); th.scope = "col"; hr.append(th); }
  thead.append(hr);
  const tbody = el("tbody");
  for (const r of rows) { const tr = el("tr"); for (const c of r) tr.append(el("td", null, c)); tbody.append(tr); }
  t.append(thead, tbody);
  return t;
}

function showTip(target, lines) {
  const tip = $("tip");
  tip.replaceChildren(el("strong", null, lines[0]), ...lines.slice(1).map((l) => el("span", null, l + " ")));
  tip.hidden = false;
  const r = target.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + "px";
  tip.style.top = (r.top - h - 8 < 8 ? r.bottom + 8 : r.top - h - 8) + "px";
}
const hideTip = () => { $("tip").hidden = true; };

function highlight(sql) {                            // tiny SQL colouring; text only, never innerHTML
  const re = /(--[^\n]*)|('[^']*')|\b(SELECT|FROM|WHERE|GROUP BY|ORDER BY|WITH|AS|CASE|WHEN|THEN|ELSE|END|AND|OR|ON|JOIN|CAST|INTEGER)\b|\b(SUM|COUNT|ROUND|ABS|AVG|substr|strftime)(?=\()|(\b\d+(?:\.\d+)?\b)/g;
  const frag = document.createDocumentFragment();
  let last = 0, m;
  while ((m = re.exec(sql))) {
    if (m.index > last) frag.append(sql.slice(last, m.index));
    frag.append(el("span", m[1] ? "c" : m[2] ? "s" : m[3] ? "k" : m[4] ? "f" : "n", m[0]));
    last = re.lastIndex;
  }
  frag.append(sql.slice(last));
  return frag;
}

function sqlBlock(d) {
  const box = el("div", "sql"), head = el("div", "sql-head");
  head.append(el("p", "sql-q", d.question), el("p", "sql-file", d.file));
  const code = el("code"); code.append(highlight(d.sql));
  const pre = el("pre"); pre.append(code);
  const foot = el("p", "sql-foot"), a = el("a", null, "docs/LEARNING.md");
  a.href = DOCS_URL;
  foot.append("Explained line by line in ", a, ".");
  box.append(head, pre, foot);
  return box;
}

function buildSqlPanels() {
  for (const region of document.querySelectorAll("[data-sql]")) {
    region.replaceChildren(...[region.dataset.sql, region.dataset.extra].filter(Boolean).map((n) => sqlBlock(D[n])));
  }
}

/* ---------- charts ---------- */
const crosshair = {
  id: "crosshair",
  afterDatasetsDraw(chart) {
    const active = chart.tooltip && chart.tooltip.getActiveElements();
    if (!active || !active.length) return;
    const x = active[0].element.x, { ctx, chartArea } = chart;
    ctx.save(); ctx.beginPath(); ctx.moveTo(x, chartArea.top); ctx.lineTo(x, chartArea.bottom);
    ctx.lineWidth = 1; ctx.strokeStyle = css("--base"); ctx.stroke(); ctx.restore();
  },
};

function tooltipBase() {
  return {
    backgroundColor: css("--surface"), titleColor: css("--muted"), bodyColor: css("--ink"),
    borderColor: css("--base"), borderWidth: 1, padding: 10, cornerRadius: 6, boxPadding: 4,
    usePointStyle: true, titleFont: { weight: "500" }, bodyFont: { weight: "600" },
  };
}

function makeCharts() {
  Chart.defaults.font.family = css("--sans");
  Chart.defaults.font.size = 12;
  Chart.defaults.color = css("--muted");
  Chart.defaults.animation = false;

  const line = (label, color, dash) => ({
    label, data: [], borderColor: color, backgroundColor: color, borderWidth: 2, borderDash: dash || [],
    borderJoinStyle: "round", borderCapStyle: "round", pointRadius: 0, pointHoverRadius: 5,
    pointHoverBorderWidth: 2, pointHoverBorderColor: css("--surface"), pointHitRadius: 14, tension: 0,
  });
  forecastChart = new Chart($("c-forecast"), {
    type: "line",
    data: { labels: [], datasets: [line("Actual offered", css("--blue")), line("Forecast", css("--forecast"), [6, 4])] },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { ...tooltipBase(), callbacks: {
          title: (items) => date(items[0].label, { weekday: "short", day: "numeric", month: "short", year: "numeric" }),
          label: (c) => `${nf.format(c.parsed.y)}  ${c.dataset.label}`,
          labelPointStyle: () => ({ pointStyle: "line", rotation: 0 }),
        } },
      },
      scales: {
        x: { grid: { display: false }, border: { color: css("--base") },
          ticks: { maxTicksLimit: 8, maxRotation: 0, callback(v) { return date(this.getLabelForValue(v), { day: "numeric", month: "short" }); } } },
        y: { beginAtZero: true, border: { display: false }, grid: { color: css("--grid") }, ticks: { callback: (v) => nf.format(v) } },
      },
    },
    plugins: [crosshair],
  });

  staffChart = new Chart($("c-staff"), {
    type: "bar",
    data: { labels: [], datasets: [{ label: "Gap", data: [], backgroundColor: [], maxBarThickness: 24, borderRadius: 4, borderSkipped: "start", categoryPercentage: 0.8, barPercentage: 0.8 }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { ...tooltipBase(), callbacks: {
          title: (items) => { const h = staffRows[items[0].dataIndex].hour; return `${hh(h)} to ${String(h).padStart(2, "0")}:59`; },
          label: (c) => { const r = staffRows[c.dataIndex];
            return [`${signed(r.gap)} agents  gap`, `${r.sched.toFixed(1)}  scheduled`, `${r.need.toFixed(1)}  needed`, `${r.shortShare.toFixed(0)}%  of half-hours short`]; },
        } },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
        y: { border: { display: false }, grid: { color: (c) => (c.tick.value === 0 ? css("--base") : css("--grid")) },
          ticks: { callback: (v) => (v > 0 ? "+" + v : String(v)) } },
      },
    },
  });
}

/* ---------- controls ---------- */
function render() {
  const kpi = selected(D.kpi), staffing = selected(D.staff);
  const days = new Set(kpi.map((r) => r.date)).size;
  const status = $("f-status");
  const qLabel = state.queue === "all" ? "All queues" : state.queue;
  status.classList.toggle("warn", days === 0);
  status.textContent = days
    ? `Showing ${qLabel}, ${state.from === state.to ? "on " + fmtDate(state.from) : fmtDate(state.from) + " to " + fmtDate(state.to)}: ${days} ${days === 1 ? "day" : "days"} with data.`
    : `No data for this selection. The data covers ${fmtDate($("f-from").min)} to ${fmtDate($("f-from").max)}, Monday to Saturday.`;
  renderKpis(kpi, staffing);
  renderForecast(selected(D.forecast));
  renderHeat(selected(D.heat));
  renderStaffing(staffing);
}

function onDateChange() {
  const from = $("f-from").value, to = $("f-to").value;
  if (!from || !to) return;
  if (from > to) {
    const s = $("f-status");
    s.classList.add("warn");
    s.textContent = "The start date must be on or before the end date.";
    return;
  }
  state.from = from; state.to = to;
  render();
}

function reset() {
  state.queue = "all";
  $("f-queue").value = "all";
  state.from = $("f-from").min; state.to = $("f-from").max;
  $("f-from").value = state.from; $("f-to").value = state.to;
  render();
}

async function init() {
  try {
    const raw = await load();
    D = { kpi: raw["01_kpi_daily"].objs, forecast: raw["02_forecast_vs_actual_daily"].objs, heat: raw["03_service_level_heatmap"].objs, staff: raw["04_staffing_gap_hourly"].objs };
    for (const name of FILES) D[name] = raw[name];     // keeps the SQL text for the "Show the SQL" panels
  } catch (err) {
    const box = $("error");
    box.hidden = false;
    box.textContent = `Could not load the data files (${err.message}). If you opened index.html directly from a folder, start a small web server instead: python -m http.server 8000 --directory dashboard, then open http://localhost:8000.`;
    return;
  }
  queues = [...new Set(D.kpi.map((r) => r.queue))].sort();
  const sel = $("f-queue");
  sel.append(new Option("All queues", "all"), ...queues.map((q) => new Option(q, q)));
  const dates = D.kpi.map((r) => r.date).sort();
  for (const id of ["f-from", "f-to"]) { $(id).min = dates[0]; $(id).max = dates[dates.length - 1]; }
  sel.addEventListener("change", () => { state.queue = sel.value; render(); });
  $("f-from").addEventListener("change", onDateChange);
  $("f-to").addEventListener("change", onDateChange);
  $("f-reset").addEventListener("click", reset);
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-toggle]");
    if (!b) return;
    const region = $(b.dataset.toggle), open = region.hidden;
    region.hidden = !open;
    b.setAttribute("aria-expanded", String(open));
  });
  makeCharts();
  buildSqlPanels();
  reset();
}

init();
