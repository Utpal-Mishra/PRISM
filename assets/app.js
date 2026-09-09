(() => {
  "use strict";

  const state = {
    data: [],
    profile: null,
    correlations: [],
    anomalies: [],
    forecast: null,
    prediction: null,
    segment: null,
    strategy: [],
    sourceName: "PRISM synthetic enterprise dataset",
    sourceMode: "Synthetic demo",
  };

  const els = {};
  const byId = (id) => document.getElementById(id);
  const numberFmt = new Intl.NumberFormat("en-IE", { maximumFractionDigits: 2 });
  const compactFmt = new Intl.NumberFormat("en-IE", { notation: "compact", maximumFractionDigits: 1 });

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    [
      "fileInput", "demoButton", "datasetName", "datasetMode", "rowCountTag", "notice",
      "metricGrid", "overviewInsights", "typeSummary", "previewTable", "downloadData",
      "correlationList", "segmentColumn", "segmentMetric", "segmentChart", "segmentTable",
      "anomalyTable", "forecastDate", "forecastMetric", "forecastHorizon", "runForecast",
      "forecastMetrics", "forecastChart", "forecastNarrative", "predictionTarget",
      "runPrediction", "predictionMetrics", "driverList", "predictionNarrative",
      "downloadStrategy", "strategyCards", "qualityMetrics", "schemaTable",
    ].forEach((id) => { els[id] = byId(id); });

    document.querySelectorAll(".nav-item").forEach((button) => {
      button.addEventListener("click", () => setView(button.dataset.view));
    });
    els.demoButton.addEventListener("click", loadDemo);
    els.fileInput.addEventListener("change", handleUpload);
    els.segmentColumn.addEventListener("change", renderSegment);
    els.segmentMetric.addEventListener("change", renderSegment);
    els.runForecast.addEventListener("click", runForecast);
    els.runPrediction.addEventListener("click", runPrediction);
    els.downloadData.addEventListener("click", downloadCurrentData);
    els.downloadStrategy.addEventListener("click", downloadStrategy);

    loadDemo();
  }

  function setView(viewName) {
    document.querySelectorAll(".nav-item").forEach((button) => {
      button.classList.toggle("active", button.dataset.view === viewName);
    });
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    const target = byId(`view-${viewName}`);
    if (target) target.classList.add("active");
    if (viewName === "relationships") renderSegment();
  }

  function mulberry32(seed) {
    return function rand() {
      let t = seed += 0x6D2B79F5;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function pick(rand, items) { return items[Math.floor(rand() * items.length)]; }
  function round(value, digits = 2) { const p = 10 ** digits; return Math.round(value * p) / p; }

  function generateDemo(rows = 840) {
    const rand = mulberry32(42026);
    const products = [
      ["P001", "Ergo Mouse", "Accessories", 69, 31, 1.1],
      ["P002", "Mechanical Keyboard", "Accessories", 119, 55, 2.0],
      ["P003", "HD Webcam", "Video", 89, 39, 1.5],
      ["P004", "Wireless Headset", "Audio", 139, 62, 1.8],
      ["P005", "Conference Speaker", "Audio", 179, 82, 2.8],
      ["P006", "Creator Light", "Video", 129, 58, 2.3],
    ];
    const regions = ["Ireland", "United Kingdom", "Germany", "France", "Netherlands"];
    const channels = ["Retail", "Online", "B2B"];
    const segments = ["Consumer", "SMB", "Enterprise"];
    const start = new Date("2024-01-01T00:00:00Z");
    const out = [];

    for (let i = 0; i < rows; i += 1) {
      const monthIndex = Math.floor(rand() * 32);
      const day = Math.floor(rand() * 27) + 1;
      const date = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + monthIndex, day));
      const [productId, productName, category, basePrice, unitCost, carbonUnit] = pick(rand, products);
      const region = pick(rand, regions);
      const channel = pick(rand, channels);
      const customerSegment = pick(rand, segments);
      const season = 1 + 0.18 * Math.sin((monthIndex / 12) * Math.PI * 2) + (date.getUTCMonth() === 10 ? 0.16 : 0);
      const trend = 1 + monthIndex * 0.012;
      const segmentLift = customerSegment === "Enterprise" ? 1.55 : customerSegment === "SMB" ? 1.2 : 1;
      const quantity = Math.max(1, Math.round((1 + rand() * 4) * segmentLift * season));
      const discount = pick(rand, [0, 0, 0, 0.05, 0.1, 0.15]);
      const priceNoise = 0.96 + rand() * 0.08;
      const unitPrice = round(basePrice * priceNoise, 2);
      const marketingSpend = round((180 + rand() * 900) * trend * (channel === "Online" ? 1.25 : 1), 2);
      const leadTimeDays = round(2.5 + rand() * 7 + (region === "Germany" ? 1.2 : 0), 1);
      const satisfactionScore = round(Math.max(1, Math.min(5, 4.65 - leadTimeDays * 0.12 + rand() * 0.7)), 2);
      const returnProbability = Math.max(0.01, 0.12 - satisfactionScore * 0.018 + discount * 0.18);
      const returned = rand() < returnProbability ? "Yes" : "No";
      const grossRevenue = quantity * unitPrice * (1 - discount) * trend;
      const revenue = round(grossRevenue * (0.92 + rand() * 0.18), 2);
      const margin = round(revenue - quantity * unitCost, 2);
      const carbonKg = round(quantity * carbonUnit * (1 + leadTimeDays * 0.025), 2);

      out.push({
        order_id: `O${String(i + 1).padStart(5, "0")}`,
        order_date: date.toISOString().slice(0, 10),
        product_id: productId,
        product_name: productName,
        category,
        region,
        channel,
        customer_segment: customerSegment,
        quantity,
        unit_price: unitPrice,
        unit_cost: unitCost,
        discount,
        marketing_spend: marketingSpend,
        lead_time_days: leadTimeDays,
        satisfaction_score: satisfactionScore,
        returned,
        revenue,
        margin,
        carbon_kg: carbonKg,
      });
    }
    return out.sort((a, b) => String(a.order_date).localeCompare(String(b.order_date)));
  }

  function loadDemo() {
    els.fileInput.value = "";
    els.demoButton.classList.add("active");
    state.sourceName = "PRISM synthetic enterprise dataset";
    state.sourceMode = "Synthetic demo";
    analyseDataset(generateDemo());
    showNotice("Synthetic demonstration data loaded. Upload a CSV/XLSX file when you want PRISM to analyse your own dataset locally in the browser.", "info");
  }

  async function handleUpload(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    els.demoButton.classList.remove("active");
    try {
      let rows;
      const lower = file.name.toLowerCase();
      if (lower.endsWith(".csv")) {
        rows = parseCSV(await file.text());
      } else if (lower.endsWith(".xlsx") || lower.endsWith(".xls")) {
        if (!window.XLSX) throw new Error("The XLSX parser has not loaded. Refresh and try again, or upload CSV.");
        const buffer = await file.arrayBuffer();
        const workbook = window.XLSX.read(buffer, { type: "array", cellDates: true });
        const sheet = workbook.Sheets[workbook.SheetNames[0]];
        rows = window.XLSX.utils.sheet_to_json(sheet, { defval: "", raw: false });
      } else {
        throw new Error("Unsupported format. Use CSV, XLSX or XLS.");
      }
      if (!rows.length) throw new Error("No data rows were found in the selected file.");
      state.sourceName = file.name;
      state.sourceMode = "Local upload";
      analyseDataset(rows);
      showNotice(`${file.name} is being analysed locally in this browser. The dataset is not sent to a PRISM application server.`, "success");
    } catch (error) {
      showNotice(`Unable to analyse the file: ${error.message}`, "error");
    }
  }

  function parseCSV(text) {
    const rows = [];
    let row = [];
    let cell = "";
    let quoted = false;
    const input = text.replace(/^\uFEFF/, "");
    for (let i = 0; i < input.length; i += 1) {
      const ch = input[i];
      if (ch === '"') {
        if (quoted && input[i + 1] === '"') { cell += '"'; i += 1; }
        else quoted = !quoted;
      } else if (ch === "," && !quoted) {
        row.push(cell); cell = "";
      } else if ((ch === "\n" || ch === "\r") && !quoted) {
        if (ch === "\r" && input[i + 1] === "\n") i += 1;
        row.push(cell); cell = "";
        if (row.some((v) => String(v).trim() !== "")) rows.push(row);
        row = [];
      } else cell += ch;
    }
    if (cell.length || row.length) { row.push(cell); rows.push(row); }
    if (rows.length < 2) return [];
    const headers = rows[0].map((h, i) => String(h || `column_${i + 1}`).trim());
    return rows.slice(1).map((values) => Object.fromEntries(headers.map((h, i) => [h, values[i] ?? ""])));
  }

  function analyseDataset(inputRows) {
    const data = inputRows.map((row) => normalizeKeys(row)).filter((row) => Object.keys(row).length > 0);
    state.data = data;
    state.profile = profileDataset(data);
    state.correlations = strongestCorrelations(data, state.profile.numericColumns);
    state.anomalies = anomalySummary(data, state.profile.numericColumns);
    state.forecast = null;
    state.prediction = null;
    state.segment = null;
    state.strategy = [];
    updateDatasetHeader();
    populateControls();
    renderAll();
  }

  function normalizeKeys(row) {
    const out = {};
    Object.entries(row || {}).forEach(([key, value], index) => {
      let name = String(key ?? "").trim() || `column_${index + 1}`;
      if (Object.prototype.hasOwnProperty.call(out, name)) name = `${name}_${index + 1}`;
      if (value instanceof Date && !Number.isNaN(value.getTime())) value = value.toISOString();
      out[name] = value;
    });
    return out;
  }

  function isMissing(value) {
    return value === null || value === undefined || String(value).trim() === "" || String(value).toLowerCase() === "nan";
  }

  function asNumber(value) {
    if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
    if (isMissing(value)) return NaN;
    const cleaned = String(value).replace(/[%€£$,]/g, "").trim();
    if (!cleaned) return NaN;
    const n = Number(cleaned);
    return Number.isFinite(n) ? n : NaN;
  }

  function asDate(value) {
    if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
    if (isMissing(value)) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function profileDataset(data) {
    const columns = Array.from(new Set(data.flatMap((row) => Object.keys(row))));
    const totalCells = Math.max(1, data.length * Math.max(columns.length, 1));
    const inventory = [];
    let missingCells = 0;
    let constants = 0;

    columns.forEach((column) => {
      const values = data.map((row) => row[column]);
      const nonMissing = values.filter((v) => !isMissing(v));
      const missing = values.length - nonMissing.length;
      missingCells += missing;
      const unique = new Set(nonMissing.map((v) => String(v))).size;
      if (unique <= 1 && nonMissing.length) constants += 1;
      const numericCount = nonMissing.reduce((acc, v) => acc + (Number.isFinite(asNumber(v)) ? 1 : 0), 0);
      const dateCount = nonMissing.reduce((acc, v) => acc + (asDate(v) ? 1 : 0), 0);
      const name = column.toLowerCase();
      const dateHint = /(date|time|month|year|week|period)/.test(name);
      const idHint = /(^id$|_id$|^id_|code|sku|order|customer_id|product_id)/.test(name);
      const numericRatio = nonMissing.length ? numericCount / nonMissing.length : 0;
      const dateRatio = nonMissing.length ? dateCount / nonMissing.length : 0;
      let role = "Text";
      if (dateHint && dateRatio >= 0.65) role = "Date";
      else if (numericRatio >= 0.86) role = "Numeric";
      else if (dateRatio >= 0.9) role = "Date";
      else if ((idHint && unique / Math.max(nonMissing.length, 1) > 0.7) || unique / Math.max(nonMissing.length, 1) > 0.94) role = "Identifier";
      else if (unique <= Math.max(60, Math.floor(data.length * 0.22))) role = "Categorical";
      inventory.push({
        column,
        role,
        missingPct: data.length ? (missing / data.length) * 100 : 0,
        unique,
        completeness: data.length ? ((data.length - missing) / data.length) * 100 : 0,
      });
    });

    const signatures = new Set();
    let duplicates = 0;
    data.forEach((row) => {
      const sig = columns.map((c) => String(row[c] ?? "")).join("\u241F");
      if (signatures.has(sig)) duplicates += 1;
      else signatures.add(sig);
    });
    const missingPct = (missingCells / totalCells) * 100;
    const duplicatePct = data.length ? (duplicates / data.length) * 100 : 0;
    const constantPct = columns.length ? (constants / columns.length) * 100 : 0;
    const qualityScore = clamp(100 - missingPct * 0.65 - duplicatePct * 1.5 - constantPct * 0.08, 0, 100);

    return {
      rows: data.length,
      columns: columns.length,
      inventory,
      missingPct,
      duplicatePct,
      duplicates,
      qualityScore,
      numericColumns: inventory.filter((r) => r.role === "Numeric").map((r) => r.column),
      dateColumns: inventory.filter((r) => r.role === "Date").map((r) => r.column),
      categoricalColumns: inventory.filter((r) => r.role === "Categorical").map((r) => r.column),
      identifierColumns: inventory.filter((r) => r.role === "Identifier").map((r) => r.column),
      textColumns: inventory.filter((r) => r.role === "Text").map((r) => r.column),
    };
  }

  function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
  function mean(values) { return values.length ? values.reduce((a, b) => a + b, 0) / values.length : NaN; }
  function sum(values) { return values.reduce((a, b) => a + b, 0); }
  function std(values) {
    if (values.length < 2) return 0;
    const m = mean(values);
    return Math.sqrt(values.reduce((acc, v) => acc + (v - m) ** 2, 0) / (values.length - 1));
  }

  function pearson(xs, ys) {
    if (xs.length < 3 || xs.length !== ys.length) return NaN;
    const mx = mean(xs); const my = mean(ys);
    let num = 0; let dx = 0; let dy = 0;
    for (let i = 0; i < xs.length; i += 1) {
      const a = xs[i] - mx; const b = ys[i] - my;
      num += a * b; dx += a * a; dy += b * b;
    }
    return dx && dy ? num / Math.sqrt(dx * dy) : NaN;
  }

  function strongestCorrelations(data, numericColumns) {
    const pairs = [];
    const cols = numericColumns.slice(0, 30);
    for (let i = 0; i < cols.length; i += 1) {
      for (let j = i + 1; j < cols.length; j += 1) {
        const xs = []; const ys = [];
        data.forEach((row) => {
          const x = asNumber(row[cols[i]]); const y = asNumber(row[cols[j]]);
          if (Number.isFinite(x) && Number.isFinite(y)) { xs.push(x); ys.push(y); }
        });
        const correlation = pearson(xs, ys);
        if (Number.isFinite(correlation) && xs.length >= 8) pairs.push({ a: cols[i], b: cols[j], correlation, n: xs.length });
      }
    }
    return pairs.sort((x, y) => Math.abs(y.correlation) - Math.abs(x.correlation)).slice(0, 15);
  }

  function quantile(sortedValues, q) {
    if (!sortedValues.length) return NaN;
    const pos = (sortedValues.length - 1) * q;
    const base = Math.floor(pos); const rest = pos - base;
    return sortedValues[base + 1] !== undefined ? sortedValues[base] + rest * (sortedValues[base + 1] - sortedValues[base]) : sortedValues[base];
  }

  function anomalySummary(data, numericColumns) {
    return numericColumns.map((column) => {
      const values = data.map((r) => asNumber(r[column])).filter(Number.isFinite).sort((a, b) => a - b);
      if (values.length < 8) return null;
      const q1 = quantile(values, 0.25); const q3 = quantile(values, 0.75); const iqr = q3 - q1;
      const low = q1 - 1.5 * iqr; const high = q3 + 1.5 * iqr;
      const outliers = values.filter((v) => v < low || v > high).length;
      return { column, outliers, outlierPct: (outliers / values.length) * 100, low, high };
    }).filter(Boolean).sort((a, b) => b.outlierPct - a.outlierPct);
  }

  function populateControls() {
    const p = state.profile;
    setOptions(els.segmentColumn, p.categoricalColumns, p.categoricalColumns.find((c) => /region|category|segment|channel/i.test(c)));
    setOptions(els.segmentMetric, p.numericColumns, preferredMetric(p.numericColumns));
    setOptions(els.forecastDate, p.dateColumns, p.dateColumns[0]);
    setOptions(els.forecastMetric, p.numericColumns, preferredMetric(p.numericColumns));
    const targetCandidates = [...p.numericColumns, ...p.categoricalColumns.filter((c) => uniqueValues(c).length <= 12)];
    setOptions(els.predictionTarget, targetCandidates, preferredPredictionTarget(targetCandidates));
  }

  function setOptions(select, values, preferred) {
    select.innerHTML = "";
    values.forEach((value) => {
      const option = document.createElement("option"); option.value = value; option.textContent = value;
      select.appendChild(option);
    });
    if (preferred && values.includes(preferred)) select.value = preferred;
    select.disabled = values.length === 0;
  }

  function preferredMetric(cols) {
    return cols.find((c) => /revenue|sales|amount|value|profit|margin|units|quantity/i.test(c)) || cols[0];
  }
  function preferredPredictionTarget(cols) {
    return cols.find((c) => /margin|revenue|sales|satisfaction|return|churn|status|outcome/i.test(c)) || cols[0];
  }
  function uniqueValues(column) { return Array.from(new Set(state.data.map((r) => r[column]).filter((v) => !isMissing(v)).map(String))); }

  function updateDatasetHeader() {
    els.datasetName.textContent = state.sourceName;
    els.datasetMode.textContent = state.sourceMode;
    els.rowCountTag.textContent = `${numberFmt.format(state.data.length)} rows`;
  }

  function renderAll() {
    renderOverview();
    renderRelationships();
    renderSegment();
    renderQuality();
    clearForecast();
    clearPrediction();
    refreshStrategy();
  }

  function metricCard(label, value, note = "") {
    return `<div class="metric-card"><div class="metric-label">${escapeHTML(label)}</div><div class="metric-value">${escapeHTML(String(value))}</div>${note ? `<div class="metric-note">${escapeHTML(note)}</div>` : ""}</div>`;
  }

  function renderOverview() {
    const p = state.profile;
    els.metricGrid.innerHTML = [
      metricCard("Rows", compactFmt.format(p.rows), "records analysed"),
      metricCard("Columns", p.columns, "fields detected"),
      metricCard("Data quality", `${p.qualityScore.toFixed(1)}%`, "completeness + duplication"),
      metricCard("Numeric", p.numericColumns.length, "measures"),
      metricCard("Dates", p.dateColumns.length, "time dimensions"),
      metricCard("Categories", p.categoricalColumns.length, "segmentable fields"),
    ].join("");

    const insights = [];
    if (p.qualityScore >= 95) insights.push("The dataset has a strong structural quality baseline for exploratory analysis. Quality scoring does not verify business correctness or source-system accuracy.");
    else insights.push(`Data quality is ${p.qualityScore.toFixed(1)}%. Review missing values, duplicates and schema roles before automating material decisions.`);
    if (state.correlations.length) {
      const c = state.correlations[0];
      insights.push(`The strongest numerical association is ${c.a} ↔ ${c.b} (r=${c.correlation.toFixed(2)}). Treat this as a relationship to investigate, not causal proof.`);
    } else insights.push("PRISM did not find enough numerical fields to calculate pairwise relationships.");
    if (p.dateColumns.length) insights.push(`Time-aware analysis is available using ${p.dateColumns.join(", ")}. Forecasting activates when a numerical measure has enough monthly history.`);
    else insights.push("No reliable date field was detected, so longitudinal trend and forecast analysis is limited.");
    if (state.anomalies[0] && state.anomalies[0].outlierPct >= 3) insights.push(`${state.anomalies[0].column} has ${state.anomalies[0].outlierPct.toFixed(1)}% potential IQR outliers. Separate legitimate business exceptions from data errors.`);
    els.overviewInsights.innerHTML = insights.map((text) => `<div class="insight">${escapeHTML(text)}</div>`).join("");

    const roles = [
      ["Numeric measures", p.numericColumns.length], ["Date fields", p.dateColumns.length],
      ["Categorical dimensions", p.categoricalColumns.length], ["Identifiers", p.identifierColumns.length],
      ["Text / other", p.textColumns.length], ["Duplicate rows", p.duplicates],
    ];
    els.typeSummary.innerHTML = roles.map(([label, value]) => `<div class="type-row"><span>${escapeHTML(label)}</span><strong>${numberFmt.format(value)}</strong></div>`).join("");
    els.previewTable.innerHTML = makeTable(state.data.slice(0, 8), Object.keys(state.data[0] || {}).slice(0, 14));
  }

  function renderRelationships() {
    if (!state.correlations.length) {
      els.correlationList.innerHTML = `<div class="empty-state">At least two usable numerical fields are required for correlation analysis.</div>`;
    } else {
      els.correlationList.innerHTML = state.correlations.map((row, i) => {
        const label = `${row.a} ↔ ${row.b}`;
        return `<div class="rank-row"><span class="rank-index">${String(i + 1).padStart(2, "0")}</span><span class="rank-name" title="${escapeAttr(label)}">${escapeHTML(label)}</span><span class="rank-value">r ${row.correlation.toFixed(2)}</span></div>`;
      }).join("");
    }
    if (!state.anomalies.length) els.anomalyTable.innerHTML = `<div class="empty-state">No numerical fields have enough observations for IQR anomaly screening.</div>`;
    else els.anomalyTable.innerHTML = makeTable(state.anomalies.slice(0, 12).map((r) => ({ field: r.column, potential_outliers: r.outliers, outlier_pct: `${r.outlierPct.toFixed(1)}%`, lower_fence: round(r.low, 2), upper_fence: round(r.high, 2) })), ["field", "potential_outliers", "outlier_pct", "lower_fence", "upper_fence"]);
  }

  function segmentPerformance(categoryColumn, metricColumn) {
    if (!categoryColumn || !metricColumn) return [];
    const groups = new Map();
    state.data.forEach((row) => {
      if (isMissing(row[categoryColumn])) return;
      const metric = asNumber(row[metricColumn]); if (!Number.isFinite(metric)) return;
      const key = String(row[categoryColumn]);
      if (!groups.has(key)) groups.set(key, { segment: key, total: 0, count: 0 });
      const g = groups.get(key); g.total += metric; g.count += 1;
    });
    const result = Array.from(groups.values()).map((g) => ({ ...g, average: g.total / g.count })).sort((a, b) => b.total - a.total).slice(0, 20);
    const total = sum(result.map((r) => r.total));
    result.forEach((r) => { r.sharePct = total ? (r.total / total) * 100 : 0; });
    return result;
  }

  function renderSegment() {
    if (els.segmentColumn.disabled || els.segmentMetric.disabled) {
      state.segment = null;
      els.segmentChart.innerHTML = `<div class="empty-state">A categorical dimension and numerical metric are required for segment analysis.</div>`;
      els.segmentTable.innerHTML = "";
      refreshStrategy();
      return;
    }
    const category = els.segmentColumn.value; const metric = els.segmentMetric.value;
    const result = segmentPerformance(category, metric);
    state.segment = { category, metric, rows: result };
    els.segmentTable.innerHTML = makeTable(result.slice(0, 10).map((r) => ({ [category]: r.segment, total: round(r.total, 2), average: round(r.average, 2), records: r.count, share: `${r.sharePct.toFixed(1)}%` })), [category, "total", "average", "records", "share"]);
    if (window.Plotly && result.length) {
      window.Plotly.newPlot(els.segmentChart, [{ type: "bar", x: result.slice(0, 10).map((r) => r.total).reverse(), y: result.slice(0, 10).map((r) => r.segment).reverse(), orientation: "h", marker: { color: "#78e2c1" }, hovertemplate: `${escapeHTML(metric)}: %{x:,.2f}<extra></extra>` }], plotLayout("", { margin: { l: 110, r: 20, t: 10, b: 35 } }), { displayModeBar: false, responsive: true });
    } else if (!result.length) els.segmentChart.innerHTML = `<div class="empty-state">No usable segment values were found.</div>`;
    refreshStrategy();
  }

  function buildMonthlySeries(dateColumn, metricColumn) {
    const buckets = new Map();
    state.data.forEach((row) => {
      const d = asDate(row[dateColumn]); const v = asNumber(row[metricColumn]);
      if (!d || !Number.isFinite(v)) return;
      const key = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
      buckets.set(key, (buckets.get(key) || 0) + v);
    });
    return Array.from(buckets.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([month, value], index) => ({ month, value, index }));
  }

  function linearFit(values) {
    const n = values.length;
    const xs = Array.from({ length: n }, (_, i) => i);
    const mx = mean(xs); const my = mean(values);
    const denom = sum(xs.map((x) => (x - mx) ** 2));
    const slope = denom ? sum(xs.map((x, i) => (x - mx) * (values[i] - my))) / denom : 0;
    return { slope, intercept: my - slope * mx };
  }

  function seasonalityFactors(series, fit) {
    if (series.length < 18) return new Map();
    const groups = new Map();
    series.forEach((point, i) => {
      const base = fit.intercept + fit.slope * i;
      if (!base) return;
      const month = Number(point.month.slice(5, 7));
      if (!groups.has(month)) groups.set(month, []);
      groups.get(month).push(point.value / base);
    });
    const factors = new Map();
    groups.forEach((values, month) => factors.set(month, clamp(mean(values), 0.55, 1.55)));
    return factors;
  }

  function nextMonth(monthKey, offset) {
    const [year, month] = monthKey.split("-").map(Number);
    const d = new Date(Date.UTC(year, month - 1 + offset, 1));
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`;
  }

  function buildForecast(series, horizon) {
    if (series.length < 6) throw new Error("At least 6 months of usable history are required.");
    const holdout = Math.max(2, Math.min(6, Math.floor(series.length * 0.2)));
    const train = series.slice(0, -holdout);
    const trainFit = linearFit(train.map((r) => r.value));
    const trainSeason = seasonalityFactors(train, trainFit);
    const holdPred = series.slice(-holdout).map((point, h) => {
      const i = train.length + h; const month = Number(point.month.slice(5, 7));
      return (trainFit.intercept + trainFit.slope * i) * (trainSeason.get(month) || 1);
    });
    const actual = series.slice(-holdout).map((r) => r.value);
    const ape = actual.map((v, i) => Math.abs(v - holdPred[i]) / Math.max(Math.abs(v), 1));
    const mape = mean(ape) * 100;

    const values = series.map((r) => r.value);
    const fit = linearFit(values); const season = seasonalityFactors(series, fit);
    const residuals = series.map((point, i) => point.value - ((fit.intercept + fit.slope * i) * (season.get(Number(point.month.slice(5, 7))) || 1)));
    const residualSd = std(residuals);
    const lastMonth = series[series.length - 1].month;
    const forecast = Array.from({ length: horizon }, (_, h) => {
      const month = nextMonth(lastMonth, h + 1); const i = series.length + h;
      const estimate = (fit.intercept + fit.slope * i) * (season.get(Number(month.slice(5, 7))) || 1);
      const uncertainty = 1.96 * residualSd * Math.sqrt(1 + (h + 1) / Math.max(series.length, 1));
      return { month, estimate, lower: Math.max(0, estimate - uncertainty), upper: estimate + uncertainty };
    });
    const recent = mean(values.slice(-Math.min(3, values.length)));
    const projected = mean(forecast.map((r) => r.estimate));
    const projectedChangePct = recent ? ((projected / recent) - 1) * 100 : 0;
    return { series, forecast, mape, holdout, projectedChangePct, slope: fit.slope };
  }

  function runForecast() {
    try {
      if (els.forecastDate.disabled || els.forecastMetric.disabled) throw new Error("A date field and numerical metric are required.");
      const dateColumn = els.forecastDate.value; const metricColumn = els.forecastMetric.value; const horizon = Number(els.forecastHorizon.value);
      const series = buildMonthlySeries(dateColumn, metricColumn);
      const result = buildForecast(series, horizon);
      state.forecast = { ...result, dateColumn, metricColumn, horizon };
      renderForecast(); refreshStrategy();
    } catch (error) {
      state.forecast = null; clearForecast();
      els.forecastNarrative.innerHTML = `<div class="insight">${escapeHTML(error.message)}</div>`;
      refreshStrategy();
    }
  }

  function renderForecast() {
    const f = state.forecast;
    els.forecastMetrics.innerHTML = [
      metricCard("History", `${f.series.length} months`, "usable monthly observations"),
      metricCard("Backtest MAPE", `${f.mape.toFixed(1)}%`, `${f.holdout}-month holdout`),
      metricCard("Projected change", `${f.projectedChangePct >= 0 ? "+" : ""}${f.projectedChangePct.toFixed(1)}%`, "forecast avg vs recent avg"),
      metricCard("Horizon", `${f.horizon} months`, "forward estimate"),
    ].join("");
    const direction = f.projectedChangePct >= 5 ? "growth" : f.projectedChangePct <= -5 ? "decline" : "broadly stable performance";
    els.forecastNarrative.innerHTML = [
      `PRISM projects ${direction} across the selected horizon: ${f.projectedChangePct >= 0 ? "+" : ""}${f.projectedChangePct.toFixed(1)}% versus the recent three-month average.`,
      `Holdout MAPE is ${f.mape.toFixed(1)}%. Treat forecast precision accordingly; this lightweight browser model is intended for transparent exploratory planning rather than production model governance.`,
    ].map((t) => `<div class="insight">${escapeHTML(t)}</div>`).join("");
    if (window.Plotly) {
      const xHist = f.series.map((r) => r.month); const yHist = f.series.map((r) => r.value);
      const xFuture = f.forecast.map((r) => r.month);
      window.Plotly.newPlot(els.forecastChart, [
        { x: xHist, y: yHist, type: "scatter", mode: "lines+markers", name: "Actual", line: { color: "#8ab4ff" } },
        { x: xFuture, y: f.forecast.map((r) => r.upper), type: "scatter", mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
        { x: xFuture, y: f.forecast.map((r) => r.lower), type: "scatter", mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: "rgba(120,226,193,.10)", name: "95% range", hoverinfo: "skip" },
        { x: xFuture, y: f.forecast.map((r) => r.estimate), type: "scatter", mode: "lines+markers", name: "Forecast", line: { color: "#78e2c1", dash: "dot" } },
      ], plotLayout(f.metricColumn, { margin: { l: 55, r: 20, t: 20, b: 45 } }), { displayModeBar: false, responsive: true });
    }
  }

  function clearForecast() {
    els.forecastMetrics.innerHTML = "";
    els.forecastChart.innerHTML = `<div class="empty-state">Choose a date field and metric, then run a forecast.</div>`;
    els.forecastNarrative.innerHTML = "";
  }

  function getModelRows(target, featureColumns) {
    return state.data.map((row, originalIndex) => {
      const targetValue = row[target];
      const features = featureColumns.map((c) => asNumber(row[c]));
      return { target: targetValue, features, originalIndex };
    }).filter((r) => !isMissing(r.target) && r.features.every(Number.isFinite));
  }

  function standardize(trainFeatures, testFeatures) {
    const width = trainFeatures[0]?.length || 0;
    const means = []; const sds = [];
    for (let j = 0; j < width; j += 1) {
      const vals = trainFeatures.map((r) => r[j]); means.push(mean(vals)); sds.push(std(vals) || 1);
    }
    const transform = (rows) => rows.map((r) => r.map((v, j) => (v - means[j]) / sds[j]));
    return { train: transform(trainFeatures), test: transform(testFeatures), means, sds };
  }

  function solveLinearSystem(matrix, vector) {
    const n = vector.length;
    const aug = matrix.map((row, i) => [...row, vector[i]]);
    for (let i = 0; i < n; i += 1) {
      let pivot = i;
      for (let r = i + 1; r < n; r += 1) if (Math.abs(aug[r][i]) > Math.abs(aug[pivot][i])) pivot = r;
      [aug[i], aug[pivot]] = [aug[pivot], aug[i]];
      if (Math.abs(aug[i][i]) < 1e-12) aug[i][i] = 1e-12;
      const div = aug[i][i];
      for (let c = i; c <= n; c += 1) aug[i][c] /= div;
      for (let r = 0; r < n; r += 1) {
        if (r === i) continue;
        const factor = aug[r][i];
        for (let c = i; c <= n; c += 1) aug[r][c] -= factor * aug[i][c];
      }
    }
    return aug.map((row) => row[n]);
  }

  function fitRidgeRegression(X, y, lambda = 0.5) {
    const xb = X.map((row) => [1, ...row]); const width = xb[0].length;
    const xtx = Array.from({ length: width }, () => Array(width).fill(0)); const xty = Array(width).fill(0);
    xb.forEach((row, i) => {
      for (let a = 0; a < width; a += 1) {
        xty[a] += row[a] * y[i];
        for (let b = 0; b < width; b += 1) xtx[a][b] += row[a] * row[b];
      }
    });
    for (let i = 1; i < width; i += 1) xtx[i][i] += lambda;
    return solveLinearSystem(xtx, xty);
  }

  function trainRegression(target, features, rows) {
    const trainRows = rows.filter((_, i) => i % 5 !== 0); const testRows = rows.filter((_, i) => i % 5 === 0);
    if (trainRows.length < 20 || testRows.length < 5) throw new Error("Not enough complete rows for a held-out regression model.");
    const yTrain = trainRows.map((r) => asNumber(r.target)); const yTest = testRows.map((r) => asNumber(r.target));
    if (![...yTrain, ...yTest].every(Number.isFinite)) throw new Error("The selected target is not consistently numerical.");
    const scaled = standardize(trainRows.map((r) => r.features), testRows.map((r) => r.features));
    const coeff = fitRidgeRegression(scaled.train, yTrain);
    const predictOne = (x) => coeff[0] + sum(x.map((v, j) => v * coeff[j + 1]));
    const pred = scaled.test.map(predictOne);
    const yMean = mean(yTest); const sse = sum(yTest.map((v, i) => (v - pred[i]) ** 2)); const sst = sum(yTest.map((v) => (v - yMean) ** 2));
    const r2 = sst ? 1 - sse / sst : 0; const mae = mean(yTest.map((v, i) => Math.abs(v - pred[i])));
    const baselineMean = mean(yTrain); const baselineMae = mean(yTest.map((v) => Math.abs(v - baselineMean)));
    const rawImp = features.map((feature, i) => ({ feature, importance: Math.abs(coeff[i + 1]) }));
    const totalImp = sum(rawImp.map((r) => r.importance)) || 1; rawImp.forEach((r) => { r.importance /= totalImp; });
    rawImp.sort((a, b) => b.importance - a.importance);
    return { type: "Regression", target, features, primaryMetric: "R²", primaryValue: r2, secondaryMetric: "MAE", secondaryValue: mae, baselineMetric: "Baseline MAE", baselineValue: baselineMae, importance: rawImp, rows: rows.length };
  }

  function trainCentroidClassifier(target, features, rows) {
    const trainRows = rows.filter((_, i) => i % 5 !== 0); const testRows = rows.filter((_, i) => i % 5 === 0);
    if (trainRows.length < 30 || testRows.length < 5) throw new Error("Not enough complete rows for a held-out classification model.");
    const classes = Array.from(new Set(rows.map((r) => String(r.target))));
    if (classes.length < 2 || classes.length > 12) throw new Error("Classification targets need between 2 and 12 distinct classes.");
    const scaled = standardize(trainRows.map((r) => r.features), testRows.map((r) => r.features));
    const centroids = new Map();
    classes.forEach((cls) => {
      const members = trainRows.map((r, i) => ({ r, x: scaled.train[i] })).filter(({ r }) => String(r.target) === cls).map(({ x }) => x);
      if (!members.length) return;
      centroids.set(cls, members[0].map((_, j) => mean(members.map((x) => x[j]))));
    });
    const predict = (x) => {
      let best = null; let bestDistance = Infinity;
      centroids.forEach((centroid, cls) => {
        const d = sum(x.map((v, j) => (v - centroid[j]) ** 2)); if (d < bestDistance) { best = cls; bestDistance = d; }
      });
      return best;
    };
    const predictions = scaled.test.map(predict); const actual = testRows.map((r) => String(r.target));
    const accuracy = mean(actual.map((v, i) => v === predictions[i] ? 1 : 0));
    const counts = new Map(); trainRows.forEach((r) => counts.set(String(r.target), (counts.get(String(r.target)) || 0) + 1));
    const baselineClass = Array.from(counts.entries()).sort((a, b) => b[1] - a[1])[0][0];
    const baselineAccuracy = mean(actual.map((v) => v === baselineClass ? 1 : 0));
    const importance = features.map((feature, j) => {
      const centroidValues = Array.from(centroids.values()).map((c) => c[j]);
      return { feature, importance: centroidValues.length > 1 ? std(centroidValues) : 0 };
    });
    const totalImp = sum(importance.map((r) => r.importance)) || 1; importance.forEach((r) => { r.importance /= totalImp; }); importance.sort((a, b) => b.importance - a.importance);
    return { type: "Classification", target, features, primaryMetric: "Accuracy", primaryValue: accuracy, secondaryMetric: "Lift vs baseline", secondaryValue: accuracy - baselineAccuracy, baselineMetric: "Baseline accuracy", baselineValue: baselineAccuracy, importance, rows: rows.length };
  }

  function runPrediction() {
    try {
      if (els.predictionTarget.disabled) throw new Error("No suitable prediction target was detected.");
      const target = els.predictionTarget.value;
      const profileRow = state.profile.inventory.find((r) => r.column === target);
      const features = state.profile.numericColumns.filter((c) => c !== target && !state.profile.identifierColumns.includes(c)).slice(0, 10);
      if (!features.length) throw new Error("At least one numerical feature is required for the browser model.");
      const rows = getModelRows(target, features);
      let result;
      if (profileRow?.role === "Numeric") result = trainRegression(target, features, rows);
      else result = trainCentroidClassifier(target, features, rows);
      state.prediction = result; renderPrediction(); refreshStrategy();
    } catch (error) {
      state.prediction = null; clearPrediction();
      els.predictionNarrative.innerHTML = `<div class="insight">${escapeHTML(error.message)}</div>`;
      refreshStrategy();
    }
  }

  function renderPrediction() {
    const p = state.prediction;
    const percentMetric = p.type === "Classification";
    const primaryDisplay = percentMetric ? `${(p.primaryValue * 100).toFixed(1)}%` : p.primaryValue.toFixed(3);
    const secondaryDisplay = p.type === "Classification" ? `${p.secondaryValue >= 0 ? "+" : ""}${(p.secondaryValue * 100).toFixed(1)} pp` : numberFmt.format(p.secondaryValue);
    const baselineDisplay = p.type === "Classification" ? `${(p.baselineValue * 100).toFixed(1)}%` : numberFmt.format(p.baselineValue);
    els.predictionMetrics.innerHTML = [
      metricCard("Model", p.type, `${p.rows} complete rows`), metricCard(p.primaryMetric, primaryDisplay, "held-out test set"),
      metricCard(p.secondaryMetric, secondaryDisplay, "model quality"), metricCard(p.baselineMetric, baselineDisplay, "simple comparator"),
    ].join("");
    els.driverList.innerHTML = p.importance.slice(0, 8).map((r, i) => `<div class="rank-row"><span class="rank-index">${String(i + 1).padStart(2, "0")}</span><span class="rank-name">${escapeHTML(r.feature)}</span><span class="rank-value">${(r.importance * 100).toFixed(1)}%</span></div>`).join("");
    const top = p.importance[0];
    const baselineStatement = p.type === "Regression" ? (p.secondaryValue < p.baselineValue ? "The model improves absolute error versus a mean-only baseline." : "The model does not beat the mean-only baseline on MAE; do not operationalise it.") : (p.primaryValue > p.baselineValue ? "The model beats the majority-class baseline on the held-out sample." : "The model does not beat the majority-class baseline; treat the current features as weak predictive evidence.");
    els.predictionNarrative.innerHTML = [
      `${top?.feature || "No field"} is the strongest model driver for ${p.target} in this run. Driver importance indicates predictive association, not causality.`,
      baselineStatement,
      "This lightweight browser model is an exploratory decision-support tool. Production models need stronger validation, leakage checks, monitoring, governance and domain review.",
    ].map((t) => `<div class="insight">${escapeHTML(t)}</div>`).join("");
  }

  function clearPrediction() {
    els.predictionMetrics.innerHTML = "";
    els.driverList.innerHTML = `<div class="empty-state">Choose a target and train a model to see predictive drivers.</div>`;
    els.predictionNarrative.innerHTML = "";
  }

  function refreshStrategy() {
    state.strategy = buildStrategy(); renderStrategy();
  }

  function buildStrategy() {
    const signals = []; const p = state.profile;
    const add = (priority, theme, evidence, recommendation, impact) => signals.push({ priority, theme, evidence, recommendation, impact });
    if (p.qualityScore < 90) add("High", "Data foundation", `Data quality is ${p.qualityScore.toFixed(1)}% with ${p.missingPct.toFixed(1)}% missing cells and ${p.duplicatePct.toFixed(1)}% duplicate rows.`, "Assign field ownership, define validation rules and resolve critical missing/duplicate records before automating high-impact decisions.", "Improves trust, repeatability and auditability of reporting and models.");
    if (p.duplicatePct >= 2) add("High", "Process control", `${p.duplicatePct.toFixed(1)}% of rows are exact duplicates.`, "Define a governed business key and add duplicate controls at ingestion rather than correcting them downstream.", "Reduces KPI inflation and duplicated operational action.");
    if (state.forecast) {
      const c = state.forecast.projectedChangePct;
      if (c <= -5) add("High", "Performance protection", `Forecast indicates ${Math.abs(c).toFixed(1)}% decline versus the recent baseline.`, "Segment the decline, validate controllable drivers and set intervention thresholds before the downside compounds.", "Supports earlier corrective action and downside planning.");
      else if (c >= 5) add("Medium", "Growth readiness", `Forecast indicates ${c.toFixed(1)}% growth versus the recent baseline.`, "Validate capacity, inventory, service levels and budget against projected growth so operational constraints do not become the limiting factor.", "Aligns resources and operating plans with expected demand.");
    }
    if (state.prediction?.importance?.length) {
      const top = state.prediction.importance[0];
      add("Medium", "Driver focus", `${top.feature} is the strongest model driver for ${state.prediction.target} (${(top.importance * 100).toFixed(1)}% relative importance).`, "Test whether the driver is controllable, validate it with domain owners and design an experiment or scenario before treating it as causal.", "Focuses investigation on variables most associated with the chosen outcome.");
    }
    if (state.correlations.length && Math.abs(state.correlations[0].correlation) >= 0.7) {
      const c = state.correlations[0];
      add("Medium", "Relationship validation", `Strong ${c.correlation >= 0 ? "positive" : "negative"} association between ${c.a} and ${c.b} (r=${c.correlation.toFixed(2)}).`, "Investigate the relationship by segment and period and check for common drivers before using it in policy, investment or operating decisions.", "Surfaces valuable relationships without overstating causality.");
    }
    if (state.segment?.rows?.length && state.segment.rows[0].sharePct >= 50) {
      const top = state.segment.rows[0];
      add("Medium", "Concentration risk", `${top.segment} contributes ${top.sharePct.toFixed(1)}% of ${state.segment.metric} across the displayed segments.`, "Stress-test dependency on the dominant segment and identify diversification, capacity or retention actions appropriate to the business context.", "Makes concentration exposure explicit for planning and risk management.");
    }
    if (state.anomalies[0]?.outlierPct >= 5) {
      const a = state.anomalies[0];
      add("Medium", "Exception management", `${a.column} has ${a.outlierPct.toFixed(1)}% potential IQR outliers.`, "Separate genuine business exceptions from data errors and add threshold-based monitoring for recurring abnormal behaviour.", "Improves control of operational exceptions and data-quality incidents.");
    }
    if (!p.dateColumns.length) add("Low", "Measurement design", "No reliable date/time field was detected.", "Add a governed temporal dimension so performance can be trended, forecast and compared before/after interventions.", "Unlocks forecasting, change detection and longitudinal strategy tracking.");
    if (!signals.length) add("Low", "Next best analysis", "No material automated risk signal was detected in the current configuration.", "Define the decision to improve, select the KPI or outcome to optimise, then use segmentation, prediction and forecasting to test the strongest available drivers.", "Moves the workflow from descriptive reporting toward decision-oriented analysis.");
    const order = { High: 0, Medium: 1, Low: 2 };
    return signals.sort((a, b) => order[a.priority] - order[b.priority]);
  }

  function renderStrategy() {
    els.strategyCards.innerHTML = state.strategy.map((s) => `<article class="strategy-card"><div class="strategy-top"><h3>${escapeHTML(s.theme)}</h3><span class="priority ${s.priority.toLowerCase()}">${escapeHTML(s.priority)}</span></div><div class="strategy-block"><span>EVIDENCE</span><p>${escapeHTML(s.evidence)}</p></div><div class="strategy-block"><span>RECOMMENDED ACTION</span><p>${escapeHTML(s.recommendation)}</p></div><div class="strategy-block"><span>DECISION IMPACT</span><p>${escapeHTML(s.impact)}</p></div></article>`).join("");
  }

  function renderQuality() {
    const p = state.profile;
    els.qualityMetrics.innerHTML = [
      metricCard("Quality score", `${p.qualityScore.toFixed(1)}%`, "structural indicator"),
      metricCard("Missing cells", `${p.missingPct.toFixed(1)}%`, "across detected fields"),
      metricCard("Duplicate rows", `${p.duplicatePct.toFixed(1)}%`, `${p.duplicates} exact duplicates`),
      metricCard("Identifiers", p.identifierColumns.length, "high-cardinality fields"),
    ].join("");
    const rows = p.inventory.map((r) => ({ field: r.column, inferred_role: r.role, completeness: `${r.completeness.toFixed(1)}%`, missing: `${r.missingPct.toFixed(1)}%`, unique_values: r.unique }));
    els.schemaTable.innerHTML = makeTable(rows, ["field", "inferred_role", "completeness", "missing", "unique_values"]);
  }

  function makeTable(rows, columns) {
    if (!rows.length || !columns.length) return `<div class="empty-state">No rows available.</div>`;
    const header = columns.map((c) => `<th>${escapeHTML(c)}</th>`).join("");
    const body = rows.map((row) => `<tr>${columns.map((c) => `<td>${escapeHTML(formatCell(row[c]))}</td>`).join("")}</tr>`).join("");
    return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
  }

  function formatCell(value) {
    if (value === null || value === undefined) return "";
    if (typeof value === "number" && Number.isFinite(value)) return numberFmt.format(value);
    const text = String(value); return text.length > 80 ? `${text.slice(0, 77)}…` : text;
  }

  function plotLayout(yTitle = "", extra = {}) {
    return {
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", font: { color: "#9fb0c3", size: 10 },
      xaxis: { gridcolor: "#1e2d40", zerolinecolor: "#1e2d40" }, yaxis: { gridcolor: "#1e2d40", zerolinecolor: "#1e2d40", title: yTitle },
      showlegend: true, legend: { orientation: "h", y: 1.08 }, margin: { l: 50, r: 20, t: 25, b: 45 }, ...extra,
    };
  }

  function rowsToCSV(rows) {
    if (!rows.length) return "";
    const columns = Array.from(new Set(rows.flatMap((r) => Object.keys(r))));
    const quote = (v) => {
      const s = v === null || v === undefined ? "" : String(v);
      return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    return `${columns.map(quote).join(",")}\n${rows.map((r) => columns.map((c) => quote(r[c])).join(",")).join("\n")}`;
  }

  function downloadCurrentData() { downloadText(rowsToCSV(state.data), "prism_analysed_data.csv", "text/csv"); }
  function downloadStrategy() {
    const rows = state.strategy.map((s) => ({ priority: s.priority, theme: s.theme, evidence: s.evidence, recommendation: s.recommendation, decision_impact: s.impact }));
    downloadText(rowsToCSV(rows), "prism_strategy_signals.csv", "text/csv");
  }
  function downloadText(content, filename, type) {
    const blob = new Blob([content], { type }); const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  function showNotice(message, kind = "info") {
    els.notice.textContent = message; els.notice.classList.remove("hidden");
    els.notice.style.borderColor = kind === "error" ? "#63323a" : kind === "success" ? "#285645" : "#35526b";
    els.notice.style.background = kind === "error" ? "#271319" : kind === "success" ? "#10251f" : "#101b28";
    els.notice.style.color = kind === "error" ? "#ffd1d1" : kind === "success" ? "#cbf8e8" : "#c8d8e7";
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }
  function escapeAttr(value) { return escapeHTML(value).replace(/`/g, "&#96;"); }
})();
