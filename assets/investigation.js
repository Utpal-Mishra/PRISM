(() => {
  "use strict";

  const VERSION = "0.6.0";
  const state = { data: [], source: "Synthetic demo", investigation: null };
  const numberFmt = new Intl.NumberFormat("en-IE", { maximumFractionDigits: 2 });
  const compactFmt = new Intl.NumberFormat("en-IE", { notation: "compact", maximumFractionDigits: 1 });

  const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  const stableHash = (value) => {
    let hash = 2166136261;
    String(value ?? "").split("").forEach((ch) => { hash ^= ch.charCodeAt(0); hash = Math.imul(hash, 16777619); });
    return (hash >>> 0).toString(36).padStart(7, "0").toUpperCase();
  };
  const slug = (value) => String(value || "dataset").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 42) || "dataset";
  const timestamp = (date = new Date()) => date.toISOString().replace(/[-:]/g, "").slice(0, 13).replace("T", "-");
  const isMissing = (value) => value === null || value === undefined || String(value).trim() === "" || String(value).toLowerCase() === "nan";
  const asNumber = (value) => {
    if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
    if (isMissing(value)) return NaN;
    const n = Number(String(value).replace(/[%€£$,]/g, "").trim());
    return Number.isFinite(n) ? n : NaN;
  };
  const asDate = (value) => {
    if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
    if (isMissing(value)) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  };

  function datasetContext() {
    const name = document.getElementById("datasetName")?.textContent?.trim() || "dataset";
    const mode = document.getElementById("datasetMode")?.textContent?.trim() || state.source;
    const rows = state.data.length;
    return { datasetId: `DS-${stableHash(`${name}|${mode}|${rows}`)}`, name, mode, rows };
  }

  function profile(data) {
    const fields = Array.from(new Set(data.flatMap((row) => Object.keys(row))));
    const numeric = [];
    const dates = [];
    const categories = [];
    fields.forEach((field) => {
      const values = data.map((row) => row[field]).filter((v) => !isMissing(v));
      if (!values.length) return;
      const nRatio = values.filter((v) => Number.isFinite(asNumber(v))).length / values.length;
      const dRatio = values.filter((v) => asDate(v)).length / values.length;
      const unique = new Set(values.map(String)).size;
      const name = field.toLowerCase();
      if ((/(date|time|month|year|week|period)/.test(name) && dRatio >= 0.65) || dRatio >= 0.9) dates.push(field);
      else if (nRatio >= 0.86 && !/(^id$|_id$|code|sku|order)/.test(name)) numeric.push(field);
      else if (unique >= 2 && unique <= Math.min(40, Math.max(8, Math.floor(data.length * 0.2)))) categories.push(field);
    });
    return { fields, numeric, dates, categories };
  }

  function monthKey(date) {
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
  }

  function choosePreferred(items, pattern) {
    return items.find((item) => pattern.test(item)) || items[0] || "";
  }

  function analyse(metric, dateField) {
    const p = profile(state.data);
    if (!metric || !dateField || !state.data.length) return { available: false, reason: "A usable date field, numerical KPI and dataset are required." };
    const periodRows = new Map();
    state.data.forEach((row) => {
      const date = asDate(row[dateField]);
      const value = asNumber(row[metric]);
      if (!date || !Number.isFinite(value)) return;
      const key = monthKey(date);
      if (!periodRows.has(key)) periodRows.set(key, []);
      periodRows.get(key).push(row);
    });
    const periods = [...periodRows.keys()].sort();
    if (periods.length < 2) return { available: false, reason: "At least two distinct time periods with usable KPI values are required." };
    const currentPeriod = periods.at(-1);
    const previousPeriod = periods.at(-2);
    const currentRows = periodRows.get(currentPeriod);
    const previousRows = periodRows.get(previousPeriod);
    const total = (rows) => rows.reduce((acc, row) => {
      const value = asNumber(row[metric]);
      return acc + (Number.isFinite(value) ? value : 0);
    }, 0);
    const current = total(currentRows);
    const previous = total(previousRows);
    const delta = current - previous;
    const pctChange = previous !== 0 ? (delta / Math.abs(previous)) * 100 : null;
    const thresholdPct = 5;
    const notable = pctChange === null ? Math.abs(delta) > 0 : Math.abs(pctChange) >= thresholdPct;

    const dimensionResults = [];
    p.categories.slice(0, 8).forEach((dimension) => {
      const groups = new Map();
      const add = (rows, side) => rows.forEach((row) => {
        if (isMissing(row[dimension])) return;
        const value = asNumber(row[metric]);
        if (!Number.isFinite(value)) return;
        const key = String(row[dimension]);
        if (!groups.has(key)) groups.set(key, { slice: key, previous: 0, current: 0 });
        groups.get(key)[side] += value;
      });
      add(previousRows, "previous");
      add(currentRows, "current");
      const slices = [...groups.values()].map((item) => ({
        ...item,
        delta: item.current - item.previous,
        contributionSharePct: delta !== 0 ? ((item.current - item.previous) / delta) * 100 : null
      })).sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
      if (slices.length) dimensionResults.push({ dimension, slices: slices.slice(0, 5) });
    });

    const allContributors = dimensionResults.flatMap((result) => result.slices.map((slice) => ({ dimension: result.dimension, ...slice })))
      .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta)).slice(0, 10);
    const top = allContributors[0] || null;
    const dataset = datasetContext();
    const investigationId = `INV-${stableHash(`${dataset.datasetId}|${metric}|${dateField}|${previousPeriod}|${currentPeriod}`)}`;
    const movementEvidenceId = `EVD-${stableHash(`${investigationId}|movement`)}`;
    const contributorEvidenceIds = allContributors.slice(0, 5).map((item, index) => `EVD-${stableHash(`${investigationId}|${index}|${item.dimension}|${item.slice}`)}`);
    const evidenceRecords = [{
      evidenceId: movementEvidenceId,
      evidenceClass: "descriptive",
      finding: `${metric} moved from ${numberFmt.format(previous)} in ${previousPeriod} to ${numberFmt.format(current)} in ${currentPeriod}.`,
      method: "Adjacent-period aggregate comparison",
      sourceFields: [metric, dateField],
      rowCount: previousRows.length + currentRows.length,
      calculation: pctChange === null ? `Delta=${numberFmt.format(delta)}; previous period was zero.` : `Delta=${numberFmt.format(delta)}; percentage change=${pctChange.toFixed(2)}%.`,
      assumptions: ["The selected KPI is meaningful when summed across records.", "Adjacent detected monthly periods are comparable."],
      confidence: { label: "Deterministic descriptive result", basis: "Calculated directly from usable records in the two latest detected periods." },
      limitations: ["This comparison does not establish why the KPI moved.", "Seasonality, mix shifts and data refresh timing may affect adjacent-period comparisons."]
    }, ...allContributors.slice(0, 5).map((item, index) => ({
      evidenceId: contributorEvidenceIds[index],
      evidenceClass: "descriptive contribution",
      finding: `${item.dimension} = ${item.slice} changed by ${numberFmt.format(item.delta)} between the compared periods.`,
      method: "Slice contribution decomposition",
      sourceFields: [metric, dateField, item.dimension],
      rowCount: previousRows.length + currentRows.length,
      calculation: item.contributionSharePct === null ? "Contribution share unavailable because total KPI delta is zero." : `Slice delta / total KPI delta = ${item.contributionSharePct.toFixed(1)}%.`,
      assumptions: ["Slice values are mutually interpretable within the selected dimension."],
      confidence: { label: "Deterministic descriptive contribution", basis: "Calculated from grouped period aggregates." },
      limitations: ["Contribution is not causation.", "Overlapping dimensions can describe the same underlying records, so contributions across different dimensions must not be added together."]
    }))];

    const path = [
      { step: 1, label: "KPI movement", detail: `${metric}: ${pctChange === null ? numberFmt.format(delta) : `${pctChange >= 0 ? "+" : ""}${pctChange.toFixed(1)}%`} (${previousPeriod} → ${currentPeriod})`, evidenceId: movementEvidenceId },
      { step: 2, label: "Where", detail: top ? `${top.dimension}: ${top.slice}` : "No low-cardinality business slice available", evidenceId: contributorEvidenceIds[0] || movementEvidenceId },
      { step: 3, label: "Main contributor", detail: top ? `${top.delta >= 0 ? "+" : ""}${compactFmt.format(top.delta)}${top.contributionSharePct === null ? "" : ` · ${top.contributionSharePct.toFixed(1)}% of net change`}` : "Insufficient categorical detail", evidenceId: contributorEvidenceIds[0] || movementEvidenceId },
      { step: 4, label: "Interpretation", detail: "Ranked slices identify where the movement is concentrated; they do not establish causal drivers.", evidenceId: movementEvidenceId }
    ];

    return {
      available: true, investigationId, dataset, metric, dateField, previousPeriod, currentPeriod,
      previous, current, delta, pctChange, thresholdPct, notable, periodRows: { previous: previousRows.length, current: currentRows.length },
      dimensions: dimensionResults, topContributors: allContributors, path, evidenceIds: evidenceRecords.map((record) => record.evidenceId), evidenceRecords,
      method: "Automated KPI movement investigation v1",
      classification: "descriptive; causal-not-established",
      generatedAt: new Date().toISOString(),
      limitations: ["The engine compares the latest two detected monthly periods.", "Metrics are aggregated by sum; users should verify that aggregation is appropriate for the selected KPI.", "Ranked slices locate concentration of change but do not prove root cause."]
    };
  }

  function generateDemo(rows = 840) {
    let seed = 42026;
    const rand = () => { let t = seed += 0x6D2B79F5; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const pick = (items) => items[Math.floor(rand() * items.length)];
    const round = (value, digits = 2) => { const p = 10 ** digits; return Math.round(value * p) / p; };
    const products = [["P001","Ergo Mouse","Accessories",69,31],["P002","Mechanical Keyboard","Accessories",119,55],["P003","HD Webcam","Video",89,39],["P004","Wireless Headset","Audio",139,62],["P005","Conference Speaker","Audio",179,82],["P006","Creator Light","Video",129,58]];
    const regions = ["Ireland","United Kingdom","Germany","France","Netherlands"];
    const channels = ["Retail","Online","B2B"];
    const segments = ["Consumer","SMB","Enterprise"];
    const start = new Date("2024-01-01T00:00:00Z");
    const out = [];
    for (let i = 0; i < rows; i += 1) {
      const monthIndex = Math.floor(rand() * 32); const day = Math.floor(rand() * 27) + 1;
      const date = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + monthIndex, day));
      const [productId, productName, category, basePrice, unitCost] = pick(products);
      const region = pick(regions); const channel = pick(channels); const customerSegment = pick(segments);
      const season = 1 + 0.18 * Math.sin((monthIndex / 12) * Math.PI * 2) + (date.getUTCMonth() === 10 ? 0.16 : 0);
      const trend = 1 + monthIndex * 0.012; const segmentLift = customerSegment === "Enterprise" ? 1.55 : customerSegment === "SMB" ? 1.2 : 1;
      const quantity = Math.max(1, Math.round((1 + rand() * 4) * segmentLift * season)); const discount = pick([0,0,0,0.05,0.1,0.15]);
      const unitPrice = round(basePrice * (0.96 + rand() * 0.08), 2); const revenue = round(quantity * unitPrice * (1 - discount) * trend * (0.92 + rand() * 0.18), 2);
      out.push({ order_id:`O${String(i+1).padStart(5,"0")}`, order_date:date.toISOString().slice(0,10), product_id:productId, product_name:productName, category, region, channel, customer_segment:customerSegment, quantity, unit_price:unitPrice, unit_cost:unitCost, discount, revenue, margin:round(revenue - quantity * unitCost,2) });
    }
    return out;
  }

  function parseCSV(text) {
    const rows = []; let row = []; let cell = ""; let quoted = false; const input = text.replace(/^\uFEFF/, "");
    for (let i = 0; i < input.length; i += 1) {
      const ch = input[i];
      if (ch === '"') { if (quoted && input[i + 1] === '"') { cell += '"'; i += 1; } else quoted = !quoted; }
      else if (ch === "," && !quoted) { row.push(cell); cell = ""; }
      else if ((ch === "\n" || ch === "\r") && !quoted) { if (ch === "\r" && input[i + 1] === "\n") i += 1; row.push(cell); cell = ""; if (row.some((v) => String(v).trim() !== "")) rows.push(row); row = []; }
      else cell += ch;
    }
    if (cell.length || row.length) { row.push(cell); rows.push(row); }
    if (rows.length < 2) return [];
    const headers = rows[0].map((h, i) => String(h || `column_${i + 1}`).trim());
    return rows.slice(1).map((values) => Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ""])));
  }

  async function readUpload(file) {
    const lower = file.name.toLowerCase();
    if (lower.endsWith(".csv")) return parseCSV(await file.text());
    if ((lower.endsWith(".xlsx") || lower.endsWith(".xls")) && window.XLSX) {
      const workbook = window.XLSX.read(await file.arrayBuffer(), { type: "array", cellDates: true });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      return window.XLSX.utils.sheet_to_json(sheet, { defval: "", raw: false });
    }
    return [];
  }

  function injectStyles() {
    if (document.getElementById("prismInvestigationStyles")) return;
    const style = document.createElement("style"); style.id = "prismInvestigationStyles";
    style.textContent = `
      .investigation-panel{margin-bottom:14px}.investigation-toolbar{display:flex;gap:9px;align-items:end;flex-wrap:wrap}.investigation-toolbar label{display:grid;gap:5px;color:var(--muted);font-size:9px;font-weight:750;text-transform:uppercase;letter-spacing:.07em}.investigation-toolbar select{min-width:150px}.investigation-actions{display:flex;gap:8px;flex-wrap:wrap}
      .investigation-banner{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:14px 0}.investigation-kpi{padding:11px;border:1px solid var(--border);border-radius:10px;background:rgba(9,21,16,.68)}.investigation-kpi span{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.07em}.investigation-kpi strong{display:block;margin-top:5px;font-size:18px}.investigation-kpi.notable{border-color:rgba(229,184,92,.4)}
      .investigation-path{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:12px 0 16px}.investigation-step{position:relative;padding:11px;border:1px solid var(--border);border-radius:10px;background:rgba(16,43,29,.32)}.investigation-step b{display:block;color:var(--accent);font-size:9px;text-transform:uppercase;letter-spacing:.08em}.investigation-step span{display:block;margin-top:5px;color:var(--soft);font-size:11px;line-height:1.45}.investigation-step small{display:block;margin-top:6px;color:var(--muted);font-size:8px}
      .investigation-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:14px}.investigation-list{display:grid;gap:7px}.investigation-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;padding:9px 10px;border:1px solid var(--border);border-radius:9px;background:rgba(9,21,16,.62)}.investigation-row strong{display:block;font-size:11px}.investigation-row small{color:var(--muted);font-size:9px}.investigation-value{text-align:right;color:var(--accent);font-size:11px;font-weight:800}.investigation-note{color:var(--muted);font-size:11px;line-height:1.55}.investigation-evidence{padding:10px 11px;border-left:2px solid var(--accent);background:rgba(16,43,29,.35);border-radius:0 8px 8px 0;font-size:10px;color:var(--soft)}
      @media(max-width:820px){.investigation-banner,.investigation-path{grid-template-columns:repeat(2,minmax(0,1fr))}.investigation-grid{grid-template-columns:1fr}.investigation-toolbar{display:grid;grid-template-columns:1fr 1fr}.investigation-toolbar label,.investigation-toolbar select{width:100%;min-width:0}.investigation-actions{grid-column:1/-1}}
      @media(max-width:390px){.investigation-banner,.investigation-path,.investigation-toolbar{grid-template-columns:1fr}.investigation-actions{grid-column:auto;display:grid}.investigation-actions button{width:100%}}
    `;
    document.head.appendChild(style);
  }

  function ensurePanel() {
    let panel = document.getElementById("automatedInvestigation");
    if (panel) return panel;
    const overview = document.getElementById("view-overview");
    const preview = document.getElementById("previewTable")?.closest(".panel");
    if (!overview || !preview) return null;
    panel = document.createElement("article"); panel.id = "automatedInvestigation"; panel.className = "panel investigation-panel";
    panel.innerHTML = `<div class="panel-heading"><div><p class="eyebrow">AUTOMATED INVESTIGATION</p><h2>KPI Movement Investigation</h2></div></div><p class="investigation-note">PRISM compares the latest two detected monthly periods, locates where a selected KPI movement is concentrated, and links each step to descriptive evidence. Concentration is not causal proof.</p><div class="investigation-toolbar"><label>KPI<select id="investigationMetric"></select></label><label>Time field<select id="investigationDate"></select></label><div class="investigation-actions"><button id="runInvestigation" class="primary-button" type="button">Run Investigation</button><button id="downloadInvestigation" class="secondary-button" type="button">Download Investigation Pack</button></div></div><div id="investigationContent"><div class="empty-state">Preparing investigation…</div></div>`;
    const semantic = document.getElementById("semanticBusinessModel");
    if (semantic?.parentNode === overview) overview.insertBefore(panel, semantic.nextSibling); else overview.insertBefore(panel, preview);
    panel.querySelector("#runInvestigation")?.addEventListener("click", runFromControls);
    panel.querySelector("#downloadInvestigation")?.addEventListener("click", downloadPack);
    return panel;
  }

  function populateControls() {
    const panel = ensurePanel(); if (!panel) return;
    const p = profile(state.data); const metricSelect = panel.querySelector("#investigationMetric"); const dateSelect = panel.querySelector("#investigationDate");
    const currentMetric = metricSelect.value; const currentDate = dateSelect.value;
    metricSelect.innerHTML = p.numeric.map((field) => `<option value="${escapeHTML(field)}">${escapeHTML(field)}</option>`).join("");
    dateSelect.innerHTML = p.dates.map((field) => `<option value="${escapeHTML(field)}">${escapeHTML(field)}</option>`).join("");
    const preferredMetric = p.numeric.includes(currentMetric) ? currentMetric : choosePreferred(p.numeric, /revenue|sales|margin|profit|units|quantity/i);
    const preferredDate = p.dates.includes(currentDate) ? currentDate : choosePreferred(p.dates, /order.*date|date|month|period/i);
    if (preferredMetric) metricSelect.value = preferredMetric; if (preferredDate) dateSelect.value = preferredDate;
    metricSelect.disabled = !p.numeric.length; dateSelect.disabled = !p.dates.length;
  }

  function runFromControls() {
    const panel = ensurePanel(); if (!panel) return;
    const metric = panel.querySelector("#investigationMetric")?.value; const dateField = panel.querySelector("#investigationDate")?.value;
    state.investigation = analyse(metric, dateField); render();
  }

  function render() {
    const panel = ensurePanel(); if (!panel) return;
    const content = panel.querySelector("#investigationContent"); const inv = state.investigation;
    if (!inv || !inv.available) { content.innerHTML = `<div class="empty-state">${escapeHTML(inv?.reason || "Load a dataset with a usable date field and numerical KPI to investigate movement.")}</div>`; return; }
    const pct = inv.pctChange === null ? "n/a" : `${inv.pctChange >= 0 ? "+" : ""}${inv.pctChange.toFixed(1)}%`;
    const banner = [["Previous", compactFmt.format(inv.previous)],["Current",compactFmt.format(inv.current)],["Net change",`${inv.delta >= 0 ? "+" : ""}${compactFmt.format(inv.delta)}`],["Movement",pct]].map(([label,value],i)=>`<div class="investigation-kpi${i===3&&inv.notable?" notable":""}"><span>${label}</span><strong>${value}</strong></div>`).join("");
    const path = inv.path.map((item) => `<div class="investigation-step"><b>${escapeHTML(item.label)}</b><span>${escapeHTML(item.detail)}</span><small>${escapeHTML(item.evidenceId)}</small></div>`).join("");
    const contributors = inv.topContributors.length ? inv.topContributors.slice(0,8).map((item,index)=>`<div class="investigation-row"><div><strong>${index+1}. ${escapeHTML(item.dimension)} · ${escapeHTML(item.slice)}</strong><small>${escapeHTML(inv.previousPeriod)} ${numberFmt.format(item.previous)} → ${escapeHTML(inv.currentPeriod)} ${numberFmt.format(item.current)}</small></div><div class="investigation-value">${item.delta>=0?"+":""}${compactFmt.format(item.delta)}${item.contributionSharePct===null?"":`<br><small>${item.contributionSharePct.toFixed(1)}% net Δ</small>`}</div></div>`).join("") : `<div class="empty-state">No suitable categorical slices were detected.</div>`;
    const evidence = inv.evidenceRecords.slice(0,5).map((record)=>`<div class="investigation-evidence"><strong>${escapeHTML(record.evidenceId)}</strong> · ${escapeHTML(record.method)}<br>${escapeHTML(record.finding)}</div>`).join("");
    content.innerHTML = `<div class="investigation-banner">${banner}</div><p class="investigation-note">${inv.notable?`Movement exceeds the ${inv.thresholdPct}% investigation threshold.`:`Movement is below the ${inv.thresholdPct}% investigation threshold; details are retained for transparency.`} ${escapeHTML(inv.classification)}.</p><div class="investigation-path">${path}</div><div class="investigation-grid"><div><p class="eyebrow">RANKED CONTRIBUTING SLICES</p><div class="investigation-list">${contributors}</div></div><div><p class="eyebrow">SUPPORTING EVIDENCE</p><div class="investigation-list">${evidence}</div><p class="investigation-note" style="margin-top:10px">Different dimensions may describe overlapping records. Do not add contribution shares across dimensions or interpret them as causal effects.</p></div></div>`;
  }

  function downloadPack() {
    const inv = state.investigation;
    if (!inv?.available) return;
    const payload = { prismVersion: VERSION, module: "Automated Analytical Investigation", ...inv, activeFilters: [], sourceMode: datasetContext().mode, disclaimer: "PRISM identifies where KPI movement is concentrated. This descriptive investigation does not establish causality or root cause." };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = `PRISM_INVESTIGATION_${slug(inv.dataset.name)}_${timestamp()}.json`; document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  }

  function refreshData(data, source) {
    state.data = Array.isArray(data) ? data.filter((row) => row && typeof row === "object") : []; state.source = source;
    populateControls(); runFromControls();
  }

  document.addEventListener("DOMContentLoaded", () => {
    injectStyles(); ensurePanel();
    refreshData(generateDemo(), "Synthetic demo");
    document.getElementById("demoButton")?.addEventListener("click", () => queueMicrotask(() => refreshData(generateDemo(), "Synthetic demo")));
    document.getElementById("fileInput")?.addEventListener("change", async (event) => {
      const file = event.target.files?.[0]; if (!file) return;
      try { const rows = await readUpload(file); refreshData(rows, "Local upload"); }
      catch (_) { refreshData([], "Local upload"); }
    });
    const datasetName = document.getElementById("datasetName");
    if (datasetName) new MutationObserver(() => { if (state.investigation?.available) { state.investigation.dataset = datasetContext(); render(); } }).observe(datasetName, { childList:true, subtree:true, characterData:true });
  });
})();