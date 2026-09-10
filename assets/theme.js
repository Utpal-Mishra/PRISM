(() => {
  "use strict";

  const tokens = Object.freeze({
    background: "#07110d",
    surface: "#0b1712",
    surface2: "#0e1d17",
    border: "#1e3229",
    text: "#edf7f1",
    muted: "#8fa39a",
    accent: "#78e6aa",
    accent2: "#52d98d",
    lime: "#c8f56b",
    warning: "#e5b85c",
    danger: "#ff7d7d",
  });

  window.PRISM_DESIGN_TOKENS = tokens;

  const replacements = new Map([
    ["#78e2c1", tokens.accent],
    ["#8ab4ff", tokens.lime],
    ["#9fb0c3", "#a9b5ae"],
    ["#1e2d40", tokens.border],
    ["rgba(120,226,193,.10)", "rgba(120,230,170,.12)"],
    ["rgba(120,226,193,0.10)", "rgba(120,230,170,.12)"],
  ]);

  function applyPalette(value, seen = new WeakSet()) {
    if (typeof value === "string") return replacements.get(value) || value;
    if (!value || typeof value !== "object") return value;
    if (seen.has(value)) return value;
    seen.add(value);

    if (Array.isArray(value)) {
      value.forEach((item, index) => { value[index] = applyPalette(item, seen); });
      return value;
    }

    Object.keys(value).forEach((key) => {
      value[key] = applyPalette(value[key], seen);
    });
    return value;
  }

  function finishLayout(layout = {}) {
    applyPalette(layout);
    layout.paper_bgcolor = "rgba(0,0,0,0)";
    layout.plot_bgcolor = "rgba(0,0,0,0)";
    layout.font = { ...(layout.font || {}), color: "#a9b5ae", family: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif' };

    ["xaxis", "yaxis"].forEach((axisName) => {
      const axis = layout[axisName] || {};
      layout[axisName] = {
        ...axis,
        gridcolor: tokens.border,
        zerolinecolor: tokens.border,
        linecolor: tokens.border,
        tickfont: { ...(axis.tickfont || {}), color: "#8fa39a" },
      };
    });
    return layout;
  }

  function patchPlotlyMethod(methodName) {
    if (!window.Plotly || typeof window.Plotly[methodName] !== "function") return;
    const original = window.Plotly[methodName].bind(window.Plotly);
    window.Plotly[methodName] = function themedPlotlyCall(graphDiv, data, layout, config, ...rest) {
      applyPalette(data);
      return original(graphDiv, data, finishLayout(layout || {}), config, ...rest);
    };
  }

  patchPlotlyMethod("newPlot");
  patchPlotlyMethod("react");
})();

(() => {
  "use strict";

  const VERSION = "0.5.0";
  const ROLES = ["Measure", "Dimension", "Identifier", "Time", "Entity", "Attribute", "Ignore"];
  const CONCEPTS = ["Revenue", "Units", "Margin", "Cost", "Spend", "Inventory", "Returns", "Price", "Discount", "Lead Time", "Satisfaction", "Carbon", "Customer", "Product", "Supplier", "Region", "Channel", "Segment", "Order", "Other"];
  const conceptRules = [
    [/revenue|sales|turnover|gmv|amount/i, "Revenue"],
    [/unit(s)?$|quantity|qty|volume/i, "Units"],
    [/margin|profit|contribution/i, "Margin"],
    [/cost|cogs|expense/i, "Cost"],
    [/spend|marketing|media|budget/i, "Spend"],
    [/inventory|stock|on_hand/i, "Inventory"],
    [/return|refund/i, "Returns"],
    [/price|asp/i, "Price"],
    [/discount|promo/i, "Discount"],
    [/lead.*time|delivery.*day/i, "Lead Time"],
    [/satisfaction|nps|csat/i, "Satisfaction"],
    [/carbon|co2|emission/i, "Carbon"],
    [/customer|client|account/i, "Customer"],
    [/product|sku|item/i, "Product"],
    [/supplier|vendor/i, "Supplier"],
    [/region|country|market|territory/i, "Region"],
    [/channel/i, "Channel"],
    [/segment/i, "Segment"],
    [/order/i, "Order"],
  ];

  const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

  function stableHash(input) {
    let hash = 2166136261;
    String(input ?? "").split("").forEach((ch) => { hash ^= ch.charCodeAt(0); hash = Math.imul(hash, 16777619); });
    return (hash >>> 0).toString(36).padStart(7, "0").toUpperCase();
  }

  function datasetContext() {
    const name = document.getElementById("datasetName")?.textContent?.trim() || "dataset";
    const mode = document.getElementById("datasetMode")?.textContent?.trim() || "unknown";
    const rowsText = document.getElementById("rowCountTag")?.textContent || "0";
    const rows = Number(rowsText.replace(/[^0-9]/g, "")) || 0;
    return { datasetId: `DS-${stableHash(`${name}|${mode}|${rows}`)}`, name, mode, rows };
  }

  function slug(value) {
    return String(value || "dataset").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 42) || "dataset";
  }

  function timestamp(date = new Date()) {
    return date.toISOString().replace(/[-:]/g, "").slice(0, 13).replace("T", "-");
  }

  function inferConcept(field) {
    return conceptRules.find(([rule]) => rule.test(field))?.[1] || "Other";
  }

  function inferSemanticRole(field, detectedRole, concept) {
    const name = field.toLowerCase();
    if (detectedRole === "Date") return "Time";
    if (detectedRole === "Identifier") return /product|customer|supplier|vendor|account/i.test(name) ? "Entity" : "Identifier";
    if (detectedRole === "Numeric") return /(^|_)(id|code|sku)($|_)/i.test(name) ? "Identifier" : "Measure";
    if (["Customer", "Product", "Supplier", "Order"].includes(concept) && /id|code|sku|name/i.test(name)) return "Entity";
    if (detectedRole === "Categorical") return "Dimension";
    return "Attribute";
  }

  function parseSchema() {
    const table = document.querySelector("#schemaTable table");
    if (!table) return [];
    const headers = [...table.querySelectorAll("thead th")].map((th) => th.textContent.trim().toLowerCase());
    const fieldIndex = headers.indexOf("field");
    const roleIndex = headers.indexOf("inferred_role");
    if (fieldIndex < 0 || roleIndex < 0) return [];
    return [...table.querySelectorAll("tbody tr")].map((tr) => {
      const cells = [...tr.querySelectorAll("td")].map((td) => td.textContent.trim());
      const field = cells[fieldIndex] || "";
      const detectedRole = cells[roleIndex] || "Text";
      const concept = inferConcept(field);
      return { field, detectedRole, semanticRole: inferSemanticRole(field, detectedRole, concept), concept };
    }).filter((row) => row.field);
  }

  function loadCorrections(datasetId) {
    try { return JSON.parse(sessionStorage.getItem(`prism-semantic:${datasetId}`) || "{}"); } catch (_) { return {}; }
  }

  function saveCorrections(datasetId, corrections) {
    try { sessionStorage.setItem(`prism-semantic:${datasetId}`, JSON.stringify(corrections)); } catch (_) { /* in-memory UI still works */ }
  }

  function injectStyles() {
    if (document.getElementById("prismSemanticStyles")) return;
    const style = document.createElement("style");
    style.id = "prismSemanticStyles";
    style.textContent = `
      .semantic-panel{margin-bottom:14px}.semantic-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:12px 0 16px}
      .semantic-stat{padding:11px;border:1px solid var(--border);border-radius:10px;background:rgba(9,21,16,.68)}.semantic-stat span{display:block;color:var(--muted);font-size:9px;text-transform:uppercase;letter-spacing:.08em}.semantic-stat strong{display:block;margin-top:4px;font-size:20px}
      .semantic-kpis{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 16px}.semantic-chip{padding:5px 8px;border:1px solid rgba(120,230,170,.18);border-radius:999px;background:var(--accent-soft);color:var(--accent);font-size:10px;font-weight:700}
      .semantic-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:14px}.semantic-editor{max-height:330px;overflow:auto;border:1px solid var(--border);border-radius:10px}.semantic-row{display:grid;grid-template-columns:minmax(120px,1.3fr) .8fr .9fr .9fr;gap:8px;align-items:center;padding:8px 10px;border-bottom:1px solid var(--border);font-size:10px}.semantic-row:last-child{border-bottom:0}.semantic-row.header{position:sticky;top:0;background:#0e1d17;color:var(--muted);font-weight:800;text-transform:uppercase;letter-spacing:.05em;z-index:1}.semantic-row select{min-width:0;width:100%;padding:6px 7px;font-size:11px}.semantic-field{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--soft)}
      .semantic-relations{display:grid;gap:7px}.semantic-relation{padding:9px 10px;border-left:2px solid var(--accent);background:rgba(16,43,29,.36);border-radius:0 8px 8px 0;color:var(--soft);font-size:11px}.semantic-note{color:var(--muted);font-size:11px;line-height:1.55}.semantic-actions{display:flex;gap:8px;flex-wrap:wrap}
      @media(max-width:820px){.semantic-grid{grid-template-columns:1fr}.semantic-summary{grid-template-columns:repeat(3,minmax(0,1fr))}.semantic-row{grid-template-columns:minmax(105px,1.2fr) .75fr .9fr}.semantic-row>*:nth-child(2){display:none}}
      @media(max-width:390px){.semantic-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.semantic-row{grid-template-columns:minmax(95px,1fr) 1fr}.semantic-row>*:nth-child(3){display:none}.semantic-actions .secondary-button{width:100%}}
    `;
    document.head.appendChild(style);
  }

  function ensurePanel() {
    let panel = document.getElementById("semanticBusinessModel");
    if (panel) return panel;
    const overview = document.getElementById("view-overview");
    const preview = overview?.querySelector("#previewTable")?.closest(".panel");
    if (!overview || !preview) return null;
    panel = document.createElement("article");
    panel.id = "semanticBusinessModel";
    panel.className = "panel semantic-panel";
    panel.innerHTML = `<div class="panel-heading"><div><p class="eyebrow">BUSINESS MODEL</p><h2>Enterprise Semantic Layer</h2></div><div class="semantic-actions"><button id="downloadSemanticModel" class="secondary-button" type="button">Download Semantic Model</button></div></div><p class="semantic-note">PRISM maps structural field types into business-readable roles and KPI concepts. These are explainable heuristics, not authoritative business definitions; correct them before governed use.</p><div id="semanticContent"><div class="empty-state">Waiting for inferred schema…</div></div>`;
    overview.insertBefore(panel, preview);
    panel.querySelector("#downloadSemanticModel")?.addEventListener("click", downloadModel);
    return panel;
  }

  function currentModel() {
    const dataset = datasetContext();
    const corrections = loadCorrections(dataset.datasetId);
    const fields = parseSchema().map((field) => ({ ...field, ...(corrections[field.field] || {}) }));
    const measures = fields.filter((f) => f.semanticRole === "Measure");
    const dimensions = fields.filter((f) => f.semanticRole === "Dimension");
    const entities = fields.filter((f) => f.semanticRole === "Entity");
    const time = fields.filter((f) => f.semanticRole === "Time");
    const identifiers = fields.filter((f) => f.semanticRole === "Identifier");
    const kpis = [...new Set(measures.map((f) => f.concept).filter((c) => c !== "Other"))];
    const anchorDimensions = [...entities, ...dimensions].slice(0, 4);
    const relationships = [];
    measures.slice(0, 4).forEach((measure) => {
      anchorDimensions.slice(0, 2).forEach((dimension) => relationships.push({ from: dimension.field, to: measure.field, type: "analytical-slice", confidence: "heuristic", statement: `${measure.field} can be analysed by ${dimension.field}.` }));
      time.slice(0, 1).forEach((dateField) => relationships.push({ from: dateField.field, to: measure.field, type: "time-series-candidate", confidence: "heuristic", statement: `${measure.field} may be trended over ${dateField.field}.` }));
    });
    return { dataset, fields, measures, dimensions, entities, time, identifiers, kpis, relationships };
  }

  function render() {
    const panel = ensurePanel();
    if (!panel) return;
    const content = panel.querySelector("#semanticContent");
    const model = currentModel();
    if (!model.fields.length) {
      content.innerHTML = `<div class="empty-state">No usable schema is available yet. Load a dataset with detected fields to build the semantic model.</div>`;
      return;
    }
    const summary = [
      ["Measures", model.measures.length], ["Dimensions", model.dimensions.length], ["Entities", model.entities.length], ["Time", model.time.length], ["Identifiers", model.identifiers.length]
    ].map(([label, value]) => `<div class="semantic-stat"><span>${label}</span><strong>${value}</strong></div>`).join("");
    const chips = model.kpis.length ? model.kpis.map((kpi) => `<span class="semantic-chip">${escapeHTML(kpi)}</span>`).join("") : `<span class="semantic-note">No standard KPI concepts were confidently detected.</span>`;
    const rows = model.fields.map((field) => `<div class="semantic-row" data-field="${escapeHTML(field.field)}"><span class="semantic-field" title="${escapeHTML(field.field)}">${escapeHTML(field.field)}</span><span>${escapeHTML(field.detectedRole)}</span><select class="semantic-role" aria-label="Business role for ${escapeHTML(field.field)}">${ROLES.map((role) => `<option${role === field.semanticRole ? " selected" : ""}>${role}</option>`).join("")}</select><select class="semantic-concept" aria-label="Business concept for ${escapeHTML(field.field)}">${CONCEPTS.map((concept) => `<option${concept === field.concept ? " selected" : ""}>${concept}</option>`).join("")}</select></div>`).join("");
    const relations = model.relationships.length ? model.relationships.slice(0, 8).map((r) => `<div class="semantic-relation">${escapeHTML(r.statement)} <span class="semantic-note">(${escapeHTML(r.confidence)} inference)</span></div>`).join("") : `<div class="empty-state">More measures and business dimensions are required to propose analytical relationships.</div>`;
    content.innerHTML = `<div class="semantic-summary">${summary}</div><p class="eyebrow">LIKELY KPI CONCEPTS</p><div class="semantic-kpis">${chips}</div><div class="semantic-grid"><div><p class="eyebrow">FIELD ROLE REVIEW</p><div class="semantic-editor"><div class="semantic-row header"><span>Field</span><span>Detected</span><span>Business role</span><span>Concept</span></div>${rows}</div></div><div><p class="eyebrow">PROBABLE RELATIONSHIPS</p><div class="semantic-relations">${relations}</div><p class="semantic-note" style="margin-top:12px">Relationships indicate valid analytical slicing or time-series candidates only. They do not assert causal or database-key relationships.</p></div></div>`;
    content.querySelectorAll(".semantic-role,.semantic-concept").forEach((select) => select.addEventListener("change", (event) => {
      const row = event.target.closest(".semantic-row");
      const field = row?.dataset.field;
      if (!field) return;
      const datasetId = datasetContext().datasetId;
      const corrections = loadCorrections(datasetId);
      corrections[field] = { semanticRole: row.querySelector(".semantic-role").value, concept: row.querySelector(".semantic-concept").value, correctedByUser: true, correctedAt: new Date().toISOString() };
      saveCorrections(datasetId, corrections);
      render();
    }));
  }

  function downloadModel() {
    const model = currentModel();
    if (!model.fields.length) return;
    const evidenceIds = [...document.querySelectorAll(".evidence-id")].map((node) => node.textContent.trim()).filter(Boolean);
    const payload = {
      prismVersion: VERSION,
      module: "Enterprise Semantic Layer",
      generatedAt: new Date().toISOString(),
      dataset: model.dataset,
      inference: {
        method: "PRISM semantic-role heuristic v1",
        basis: "Detected structural role plus explainable field-name patterns",
        confidence: "heuristic; user review required for governed use",
        limitations: ["Business meaning cannot be established from field names and structural types alone.", "Proposed relationships support analysis but do not establish causality or database key constraints."]
      },
      evidenceIds,
      kpiConcepts: model.kpis,
      fields: model.fields,
      relationships: model.relationships,
      correctionScope: "Browser session only",
      sourceMode: model.dataset.mode
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `PRISM_SEMANTIC_${slug(model.dataset.name)}_${timestamp()}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  document.addEventListener("DOMContentLoaded", () => {
    injectStyles();
    ensurePanel();
    const schema = document.getElementById("schemaTable");
    if (!schema) return;
    let queued = false;
    const refresh = () => {
      if (queued) return;
      queued = true;
      queueMicrotask(() => { queued = false; render(); });
    };
    new MutationObserver(refresh).observe(schema, { childList: true, subtree: true });
    const name = document.getElementById("datasetName");
    if (name) new MutationObserver(refresh).observe(name, { childList: true, subtree: true, characterData: true });
    refresh();
  });
})();
