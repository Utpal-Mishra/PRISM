(() => {
  "use strict";

  const MOBILE_BREAKPOINT = 820;

  document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const sidebar = document.getElementById("sidebar");
    const menuToggle = document.getElementById("menuToggle");
    const sidebarBackdrop = document.getElementById("sidebarBackdrop");
    const introToggle = document.getElementById("introToggle");
    const introDetails = document.getElementById("introDetails");

    if (!sidebar || !menuToggle || !sidebarBackdrop || !introToggle || !introDetails) return;

    const isMobile = () => window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`).matches;
    const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let lastMobileState = isMobile();
    let layoutTimer = null;
    let chartTimer = null;

    function resizeCharts() {
      if (!window.Plotly || !window.Plotly.Plots) return;
      document.querySelectorAll(".chart .js-plotly-plot").forEach((plot) => {
        if (plot.offsetParent !== null) {
          try {
            window.Plotly.Plots.resize(plot);
          } catch (_) {
            // Plotly may still be initialising; the app's responsive config remains the fallback.
          }
        }
      });
    }

    function scheduleChartResize(delay = 80) {
      window.clearTimeout(chartTimer);
      chartTimer = window.setTimeout(resizeCharts, delay);
    }

    function openSidebar() {
      if (!isMobile()) return;
      body.classList.add("sidebar-open");
      sidebar.setAttribute("aria-hidden", "false");
      menuToggle.setAttribute("aria-expanded", "true");
      menuToggle.setAttribute("aria-label", "Close navigation");
    }

    function closeSidebar({ restoreFocus = false } = {}) {
      body.classList.remove("sidebar-open");
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Open navigation");
      if (isMobile()) sidebar.setAttribute("aria-hidden", "true");
      else sidebar.removeAttribute("aria-hidden");
      if (restoreFocus && isMobile()) menuToggle.focus();
    }

    function toggleSidebar() {
      if (body.classList.contains("sidebar-open")) closeSidebar({ restoreFocus: true });
      else openSidebar();
    }

    function setIntro(open) {
      introDetails.classList.toggle("is-open", open);
      introToggle.setAttribute("aria-expanded", String(open));
      introToggle.setAttribute("aria-label", open ? "Hide introduction" : "Show introduction");
      scheduleChartResize(220);
    }

    function scrollViewToTop() {
      if (!isMobile()) return;
      window.scrollTo({ top: 0, behavior: reduceMotion() ? "auto" : "smooth" });
    }

    function syncLayout(force = false) {
      const mobile = isMobile();
      if (!force && mobile === lastMobileState) {
        scheduleChartResize();
        return;
      }

      lastMobileState = mobile;
      if (mobile) {
        closeSidebar();
        setIntro(false);
        sidebar.setAttribute("aria-hidden", "true");
      } else {
        body.classList.remove("sidebar-open");
        sidebar.removeAttribute("aria-hidden");
        menuToggle.setAttribute("aria-expanded", "false");
        setIntro(true);
      }
      scheduleChartResize(120);
    }

    menuToggle.addEventListener("click", toggleSidebar);
    sidebarBackdrop.addEventListener("click", () => closeSidebar({ restoreFocus: true }));
    introToggle.addEventListener("click", () => setIntro(!introDetails.classList.contains("is-open")));

    document.querySelectorAll(".nav-item").forEach((button) => {
      button.addEventListener("click", () => {
        if (isMobile()) {
          closeSidebar();
          scrollViewToTop();
          scheduleChartResize(140);
        }
      });
    });

    const fileInput = document.getElementById("fileInput");
    if (fileInput) fileInput.addEventListener("change", () => {
      if (isMobile()) closeSidebar();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        if (body.classList.contains("sidebar-open")) closeSidebar({ restoreFocus: true });
        else if (isMobile() && introDetails.classList.contains("is-open")) setIntro(false);
      }
    });

    window.addEventListener("resize", () => {
      window.clearTimeout(layoutTimer);
      layoutTimer = window.setTimeout(() => syncLayout(false), 120);
    });

    window.addEventListener("orientationchange", () => {
      closeSidebar();
      window.setTimeout(() => {
        lastMobileState = isMobile();
        scheduleChartResize(120);
      }, 180);
    });

    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", () => scheduleChartResize(120));
    }

    syncLayout(true);
  });
})();


(() => {
  "use strict";

  const PRISM_VERSION = "0.4.0";
  const evidenceStore = [];

  const escapeHTML = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
  }[char]));

  function stableHash(value) {
    let hash = 2166136261;
    const input = String(value ?? "");
    for (let i = 0; i < input.length; i += 1) {
      hash ^= input.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(36).padStart(7, "0").toUpperCase();
  }

  function datasetContext() {
    const name = document.getElementById("datasetName")?.textContent?.trim() || "dataset";
    const mode = document.getElementById("datasetMode")?.textContent?.trim() || "unknown";
    const rowsText = document.getElementById("rowCountTag")?.textContent || "0";
    const rows = Number(rowsText.replace(/[^0-9]/g, "")) || 0;
    const metricCards = [...document.querySelectorAll("#metricGrid .metric-card")];
    const qualityCard = metricCards.find((card) => /data quality/i.test(card.querySelector(".metric-label")?.textContent || ""));
    const qualityScore = qualityCard ? Number((qualityCard.querySelector(".metric-value")?.textContent || "").replace("%", "")) : null;
    const datasetId = `DS-${stableHash(`${name}|${mode}|${rows}`)}`;
    return { datasetId, name, mode, rows, qualityScore };
  }

  function classifyFinding(text) {
    if (/strongest numerical association/i.test(text)) {
      const match = text.match(/association is (.+?) ↔ (.+?) \(r=([+-]?[0-9.]+)\)/i);
      return {
        evidenceClass: "association",
        method: "Pearson correlation screening",
        sourceFields: match ? [match[1], match[2]] : [],
        calculation: match ? `Pearson r=${match[3]}` : "Pearson correlation coefficient",
        assumptions: ["Paired numeric observations are treated as comparable.", "The coefficient describes linear association only."],
        confidence: { label: "Exploratory association", basis: "Magnitude is shown for investigation; statistical significance is not asserted in this stage." },
        limitations: ["Correlation does not establish causation.", "No multiple-testing correction is applied in the exploratory screen."]
      };
    }
    if (/data quality|structural quality baseline/i.test(text)) {
      return {
        evidenceClass: "descriptive",
        method: "Structural data-quality profiling",
        sourceFields: ["Dataset-wide structural profile"],
        calculation: "Quality score based on missingness, exact duplicates and constant-field penalties.",
        assumptions: ["Structural quality indicators are proxies for analytical readiness."],
        confidence: { label: "High for structure", basis: "Calculated deterministically from the active dataset profile." },
        limitations: ["Does not verify business correctness, source-system accuracy, freshness or semantic validity."]
      };
    }
    if (/time-aware analysis|date field/i.test(text)) {
      const match = text.match(/using (.+?)\. Forecasting/i);
      return {
        evidenceClass: "descriptive",
        method: "Date-role inference",
        sourceFields: match ? match[1].split(",").map((value) => value.trim()) : [],
        calculation: "Role inference from field name hints and parseable date values.",
        assumptions: ["Detected date formats are representative of the field."],
        confidence: { label: "Detected role", basis: "One or more fields passed PRISM date-role thresholds, or no field met those thresholds." },
        limitations: ["Forecast suitability also depends on history length, granularity and usable measures."]
      };
    }
    if (/potential IQR outliers/i.test(text)) {
      const field = text.split(" has ")[0]?.trim();
      return {
        evidenceClass: "descriptive",
        method: "IQR outlier screening",
        sourceFields: field ? [field] : [],
        calculation: "Potential outliers fall outside Q1 - 1.5×IQR and Q3 + 1.5×IQR.",
        assumptions: ["IQR fences are a screening heuristic, not an error classifier."],
        confidence: { label: "Screening signal", basis: "Based on the proportion of usable values outside IQR fences." },
        limitations: ["Legitimate business exceptions may be flagged as outliers."]
      };
    }
    return {
      evidenceClass: "descriptive",
      method: "Automated dataset interpretation",
      sourceFields: [],
      calculation: null,
      assumptions: [],
      confidence: { label: "Context only", basis: "The finding is generated from the current local analytical profile." },
      limitations: ["Review source data and domain context before material decisions."]
    };
  }

  function createEvidenceRecord(text, index) {
    const dataset = datasetContext();
    const detail = classifyFinding(text);
    const evidenceId = `EVD-${stableHash(`${dataset.datasetId}|${index}|${text}`)}`;
    return {
      evidenceId,
      finding: text,
      evidenceClass: detail.evidenceClass,
      datasetId: dataset.datasetId,
      datasetName: dataset.name,
      sourceMode: dataset.mode,
      rowCount: dataset.rows,
      sourceFields: detail.sourceFields,
      filters: [],
      method: detail.method,
      calculation: detail.calculation,
      assumptions: detail.assumptions,
      qualityScore: dataset.qualityScore,
      confidence: detail.confidence,
      limitations: detail.limitations,
      calculationVersion: "evidence-v1",
      generatedAt: new Date().toISOString()
    };
  }

  function detailHTML(record) {
    const fields = record.sourceFields.length ? record.sourceFields.join(", ") : "No specific fields";
    const assumptions = record.assumptions.length ? record.assumptions.join(" • ") : "None recorded";
    const limitations = record.limitations.length ? record.limitations.join(" • ") : "None recorded";
    return `
      <div class="evidence-meta-grid">
        <div><span>Evidence ID</span><strong>${escapeHTML(record.evidenceId)}</strong></div>
        <div><span>Evidence class</span><strong>${escapeHTML(record.evidenceClass)}</strong></div>
        <div><span>Dataset</span><strong>${escapeHTML(record.datasetId)}</strong></div>
        <div><span>Rows analysed</span><strong>${record.rowCount.toLocaleString("en-IE")}</strong></div>
        <div><span>Method</span><strong>${escapeHTML(record.method)}</strong></div>
        <div><span>Confidence</span><strong>${escapeHTML(record.confidence.label)}</strong></div>
      </div>
      <p><b>Source fields:</b> ${escapeHTML(fields)}</p>
      ${record.calculation ? `<p><b>Calculation:</b> ${escapeHTML(record.calculation)}</p>` : ""}
      <p><b>Confidence basis:</b> ${escapeHTML(record.confidence.basis)}</p>
      <p><b>Assumptions:</b> ${escapeHTML(assumptions)}</p>
      <p><b>Limitations:</b> ${escapeHTML(limitations)}</p>
      <p><b>Active filters:</b> None · <b>Calculation version:</b> ${escapeHTML(record.calculationVersion)}</p>`;
  }

  function enhanceInsights() {
    const container = document.getElementById("overviewInsights");
    if (!container) return;
    const insights = [...container.querySelectorAll(":scope > .insight")];
    if (!insights.length) return;

    evidenceStore.length = 0;
    insights.forEach((node, index) => {
      const text = (node.dataset.findingText || node.textContent || "").trim();
      if (!text) return;
      node.dataset.findingText = text;
      const record = createEvidenceRecord(text, index);
      evidenceStore.push(record);
      node.classList.add("evidence-insight");
      node.innerHTML = `
        <div class="evidence-insight-top">
          <span class="evidence-id">${escapeHTML(record.evidenceId)}</span>
          <span class="evidence-class">${escapeHTML(record.evidenceClass)}</span>
        </div>
        <p>${escapeHTML(record.finding)}</p>
        <button class="evidence-toggle" type="button" aria-expanded="false">View evidence</button>
        <div class="evidence-detail hidden">${detailHTML(record)}</div>`;
      node.querySelector(".evidence-toggle").addEventListener("click", (event) => {
        const button = event.currentTarget;
        const detail = node.querySelector(".evidence-detail");
        const expanded = button.getAttribute("aria-expanded") === "true";
        button.setAttribute("aria-expanded", String(!expanded));
        button.textContent = expanded ? "View evidence" : "Hide evidence";
        detail.classList.toggle("hidden", expanded);
      });
    });

    const summary = document.getElementById("evidencePackSummary");
    if (summary) {
      const dataset = datasetContext();
      summary.textContent = `${evidenceStore.length} traceable evidence record${evidenceStore.length === 1 ? "" : "s"} · ${dataset.datasetId}`;
    }
  }

  function exportTimestamp(date = new Date()) {
    return date.toISOString().replace(/[-:]/g, "").slice(0, 13).replace("T", "-");
  }

  function datasetSlug() {
    const name = datasetContext().name;
    return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 42) || "dataset";
  }

  function downloadEvidencePack() {
    if (!evidenceStore.length) {
      const notice = document.getElementById("notice");
      if (notice) {
        notice.textContent = "No evidence records are available for export.";
        notice.classList.remove("hidden");
      }
      return;
    }
    const pack = {
      prismVersion: PRISM_VERSION,
      module: "Evidence Foundation",
      generatedAt: new Date().toISOString(),
      dataset: datasetContext(),
      activeFilters: [],
      recordCount: evidenceStore.length,
      evidenceRecords: evidenceStore,
      disclaimer: "PRISM evidence supports analytical review. Association does not establish causation; accountable domain owners should validate material decisions."
    };
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `PRISM_EVIDENCE_${datasetSlug()}_${exportTimestamp()}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("overviewInsights");
    if (!container) return;

    const heading = container.closest(".panel")?.querySelector(".panel-heading");
    if (heading && !document.getElementById("downloadEvidence")) {
      const titleBlock = heading.querySelector("div");
      const summary = document.createElement("p");
      summary.id = "evidencePackSummary";
      summary.className = "panel-meta";
      titleBlock?.appendChild(summary);

      const button = document.createElement("button");
      button.id = "downloadEvidence";
      button.className = "secondary-button";
      button.type = "button";
      button.textContent = "Download Evidence Pack";
      heading.appendChild(button);
    }

    const existingButton = document.getElementById("downloadEvidence");
    if (existingButton && !existingButton.dataset.evidenceBound) {
      existingButton.dataset.evidenceBound = "true";
      existingButton.addEventListener("click", downloadEvidencePack);
    }
    let pending = false;
    const observer = new MutationObserver(() => {
      if (pending) return;
      const needsEnhancement = [...container.querySelectorAll(":scope > .insight")].some((node) => !node.classList.contains("evidence-insight"));
      if (!needsEnhancement) return;
      pending = true;
      queueMicrotask(() => {
        enhanceInsights();
        pending = false;
      });
    });
    observer.observe(container, { childList: true });
    enhanceInsights();
  });
})();
