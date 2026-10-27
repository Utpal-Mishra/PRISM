(() => {
  "use strict";

  const VERSION = "1.8.0";
  const METHOD_VERSION = "copilot-evidence-first-1.0.0";
  const PROVIDER = "deterministic-local";
  const STORE_KEYS = {
    strategy: "prism.strategy.v2",
    decisions: "prism.decisions.v1",
    outcomes: "prism.outcomes.v1",
    registry: "prism_registry_v1",
    governance: "prism.governance.v1"
  };
  const providers = new Map();
  let activeProvider = PROVIDER;
  let latestBrief = null;

  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const safe = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key) || JSON.stringify(fallback)); } catch (_) { return fallback; } };
  const slug = (v) => safe(v).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 42) || "dataset";
  const stamp = (date = new Date()) => {
    const p = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}${p(date.getMonth()+1)}${p(date.getDate())}-${p(date.getHours())}${p(date.getMinutes())}`;
  };
  const stop = new Set("a an the and or of to for in on at by with from is are was were be been being this that these those what why how which who when where did does do can could should would will may might my our your their it its about into over under than then next last current recent please show tell explain give find identify analyse analyze data dataset prism".split(" "));
  const tokenise = (v) => [...new Set(safe(v).toLowerCase().replace(/[^a-z0-9_%.-]+/g, " ").split(/\s+/).filter((t) => t.length > 2 && !stop.has(t)))];

  function datasetMeta() {
    const state = window.PRISM_STATE || window.prismState || {};
    const name = document.getElementById("datasetName")?.textContent?.trim() || "PRISM dataset";
    return {
      name,
      rows: Array.isArray(state.data) ? state.data.length : Number((document.getElementById("rowCountTag")?.textContent || "0").replace(/[^0-9]/g, "")) || 0,
      source_mode: document.getElementById("datasetMode")?.textContent?.trim() || "Browser-local"
    };
  }

  function intentFor(query) {
    const q = safe(query).toLowerCase();
    if (/outcome|did it work|actual|effectiveness|learn|result/.test(q)) return "outcome";
    if (/decision|approve|approved|owner|accountab|govern/.test(q)) return "decision";
    if (/strategy|recommend|what should|action|option|alternative/.test(q)) return "strategy";
    if (/forecast|future|next|predict|projection|uncertainty/.test(q)) return "forecast";
    if (/why|driver|root.?cause|declin|increase|decrease|change|movement|contribut/.test(q)) return "driver";
    if (/correl|relationship|association|segment/.test(q)) return "relationship";
    if (/quality|missing|duplicate|schema|field|completeness/.test(q)) return "quality";
    if (/metric|definition|formula|registry|lineage|source/.test(q)) return "definition";
    return "overview";
  }

  function addEvidence(map, id, type, text, metadata = {}) {
    if (!id || !/^EVD-[A-Z0-9-]+$/i.test(id)) return;
    const context = safe(text);
    if (!context) return;
    const key = id.toUpperCase();
    const record = { evidence_id: key, type, text: context.slice(0, 1200), metadata };
    const existing = map.get(key);
    if (!existing || record.text.length < existing.text.length || type !== "workspace") map.set(key, record);
  }

  function collectDomEvidence(map) {
    const selector = ".evidence-insight,.investigation-evidence,.driver-evidence,.strategy-card,.insight-item,.insight,article,p,li,tr";
    document.querySelectorAll(selector).forEach((node) => {
      const text = safe(node.innerText || node.textContent);
      if (!text || text.length > 1800) return;
      const ids = text.match(/EVD-[A-Z0-9-]+/gi) || [];
      ids.forEach((id) => addEvidence(map, id, "workspace", text, { source: "active-workspace" }));
    });
  }

  function collectPersistedEvidence(map) {
    const strategy = read(STORE_KEYS.strategy, null);
    if (strategy && Array.isArray(strategy.evidence_ids)) {
      strategy.evidence_ids.forEach((id) => addEvidence(map, id, "strategy",
        [strategy.problem, strategy.hypothesis, strategy.recommended_action, strategy.kpi_to_monitor, strategy.confidence, strategy.risk].filter(Boolean).join(" · "),
        { strategy_id: strategy.strategy_id, classification: strategy.classification }));
    }

    const decisions = read(STORE_KEYS.decisions, []);
    if (Array.isArray(decisions)) decisions.forEach((d) => (d.evidence_ids || []).forEach((id) => addEvidence(map, id, "decision",
      [d.selected_action, d.expected_outcome, d.kpi_to_monitor, d.owner, d.status].filter(Boolean).join(" · "),
      { decision_id: d.decision_id, strategy_id: d.strategy_id, classification: d.classification })));

    const outcomes = read(STORE_KEYS.outcomes, []);
    if (Array.isArray(outcomes)) outcomes.forEach((o) => (o.evidence_ids || []).forEach((id) => addEvidence(map, id, "outcome",
      [o.kpi, `expected ${o.expected_kpi}`, `actual ${o.actual_kpi}`, `variance ${o.variance}`, o.assessment, o.learning].filter(Boolean).join(" · "),
      { outcome_id: o.outcome_id, decision_id: o.decision_id, classification: o.classification })));

    const registry = read(STORE_KEYS.registry, {datasets:[], metrics:[]});
    [...(registry.datasets || []), ...(registry.metrics || [])].forEach((obj) => {
      const ev = obj.evidence;
      if (ev?.evidence_id) addEvidence(map, ev.evidence_id, "definition",
        [obj.name, obj.description || obj.definition, obj.formula, (obj.source_fields || []).join(", "), obj.owner, obj.certification].filter(Boolean).join(" · "),
        { object_id: obj.id, classification: ev.classification });
    });

    const governance = read(STORE_KEYS.governance, {controls:[]});
    (governance.controls || []).forEach((control) => {
      const ev = control.evidence;
      if (ev?.evidence_id) addEvidence(map, ev.evidence_id, "governance",
        [control.asset, control.actor, control.role, control.approval_state, control.data_classification, control.model_governance?.model_or_method, control.model_governance?.intended_use].filter(Boolean).join(" · "),
        { control_id: control.control_id, classification: ev.classification });
    });
  }

  function collectEvidence() {
    const map = new Map();
    collectDomEvidence(map);
    collectPersistedEvidence(map);
    return [...map.values()];
  }

  function typeBoost(intent, type) {
    const boosts = {
      driver: {workspace:4, strategy:2},
      relationship: {workspace:4},
      forecast: {workspace:5},
      strategy: {strategy:7, decision:2, workspace:2},
      decision: {decision:7, governance:4, strategy:3},
      outcome: {outcome:8, decision:3},
      quality: {workspace:5, definition:2},
      definition: {definition:8, governance:2},
      overview: {workspace:3, strategy:2, decision:1, outcome:1}
    };
    return boosts[intent]?.[type] || 0;
  }

  function rankEvidence(query, evidence, intent) {
    const terms = tokenise(query);
    return evidence.map((record) => {
      const hay = safe(record.text).toLowerCase();
      let score = typeBoost(intent, record.type);
      terms.forEach((term) => { if (hay.includes(term)) score += term.length >= 7 ? 4 : 3; });
      if (terms.length && terms.every((term) => hay.includes(term))) score += 4;
      return {...record, score};
    }).sort((a,b) => b.score - a.score || a.text.length - b.text.length);
  }

  function nextAction(intent) {
    const actions = {
      driver: "Use Driver & Root-Cause plus Scenario Studio to test controllable hypotheses. Concentration or association is not causal proof.",
      relationship: "Inspect Relationships and Statistical Evidence before treating an association as decision evidence.",
      forecast: "Open Forecast Intelligence to inspect candidate-model comparison, holdout error and uncertainty before using the projection.",
      strategy: "Review the cited strategy proposal with an accountable domain owner, then record any approved action in the Decision Register.",
      decision: "Verify owner, approval state, evidence links and review date. Material actions remain human-approved.",
      outcome: "Compare the recorded expectation with the observed KPI and retain concurrent-change limitations; outcome alignment does not isolate causal impact.",
      quality: "Resolve material quality/schema issues before relying on downstream analytical or strategy outputs.",
      definition: "Confirm governed dataset/metric definitions and lineage before treating the term as an authoritative enterprise KPI.",
      overview: "Open the cited evidence records to inspect method, assumptions and limitations before making a material decision."
    };
    return actions[intent] || actions.overview;
  }

  function classification(intent) {
    if (intent === "forecast") return "predictive evidence synthesis; causal-not-established";
    if (intent === "decision") return "governed decision-context synthesis; human approval required";
    if (intent === "outcome") return "observational outcome synthesis; causal-not-established";
    if (intent === "definition") return "governance/definition synthesis; not analytical proof";
    return "descriptive/associative evidence synthesis; causal-not-established";
  }

  function concise(text) {
    let value = safe(text).replace(/\bEVD-[A-Z0-9-]+\b/gi, "").replace(/\s+·\s+·/g, " · ").trim();
    if (value.length > 310) value = value.slice(0, 307).replace(/\s+\S*$/, "") + "…";
    return value;
  }

  function composeLocal(query, evidence) {
    const intent = intentFor(query);
    const ranked = rankEvidence(query, evidence, intent);
    const queryTerms = tokenise(query);
    const hasSpecificTerms = queryTerms.length > 0;
    const threshold = hasSpecificTerms ? 5 : 2;
    const selected = ranked.filter((r) => r.score >= threshold).slice(0, 4);

    if (!selected.length) {
      return {
        ok: false,
        intent,
        classification: classification(intent),
        answer: "PRISM does not have enough traceable evidence in the current workspace to answer that question reliably.",
        guidance: intent === "forecast"
          ? "Run Forecast Intelligence for the relevant KPI first, then ask again."
          : intent === "driver"
            ? "Run Automated Investigation / Driver & Root-Cause for the relevant KPI first, then ask again."
            : "Generate or load the relevant analytical evidence first, then ask again.",
        citations: []
      };
    }

    return {
      ok: true,
      intent,
      classification: classification(intent),
      answer: selected.map((r) => concise(r.text)).filter(Boolean),
      guidance: nextAction(intent),
      citations: selected.map((r) => r.evidence_id),
      evidence: selected
    };
  }

  function validateProviderResult(result, evidence) {
    const allowed = new Set(evidence.map((e) => e.evidence_id));
    const citations = Array.isArray(result?.citations) ? result.citations.filter((id) => allowed.has(String(id).toUpperCase())) : [];
    if (!result || !result.answer || !citations.length) {
      return {ok:false, answer:"The configured provider did not return an evidence-grounded answer with valid PRISM evidence citations.", guidance:"Use the local evidence composer or generate more evidence.", citations:[]};
    }
    return {...result, ok:true, citations};
  }

  async function ask(query) {
    const evidence = collectEvidence();
    if (activeProvider === PROVIDER || !providers.has(activeProvider)) return composeLocal(query, evidence);
    try {
      const raw = await providers.get(activeProvider).compose({query, evidence, dataset: datasetMeta(), method_version: METHOD_VERSION});
      return validateProviderResult(raw, evidence);
    } catch (_) {
      return {ok:false, answer:"The configured provider could not produce a validated evidence-grounded response.", guidance:"PRISM has not sent the question elsewhere automatically; switch back to the local composer or review provider configuration.", citations:[]};
    }
  }

  function renderResult(result, query) {
    const host = document.getElementById("copilotResult");
    if (!host) return;
    const findings = Array.isArray(result.answer) ? result.answer : [result.answer];
    const citations = (result.citations || []).map((id) => `<button class="copilot-citation" type="button" data-evidence="${esc(id)}">${esc(id)}</button>`).join("");
    host.innerHTML = `
      <div class="copilot-result-head"><span class="tag">${result.ok ? "Evidence grounded" : "Insufficient evidence"}</span><span class="tag muted">${esc(result.classification || "evidence validation")}</span></div>
      <h3>${result.ok ? "PRISM answer" : "PRISM refusal"}</h3>
      <div class="copilot-findings">${findings.filter(Boolean).map((f) => `<div class="insight-item"><p>${esc(f)}</p></div>`).join("")}</div>
      ${citations ? `<div class="copilot-citations"><strong>Evidence:</strong> ${citations}</div>` : ""}
      <p class="copilot-guidance"><strong>Next:</strong> ${esc(result.guidance || "")}</p>
      <small>Method: ${METHOD_VERSION} · Provider: ${esc(activeProvider)} · PRISM will not convert association into causal proof.</small>`;
    host.querySelectorAll(".copilot-citation").forEach((button) => button.addEventListener("click", () => focusEvidence(button.dataset.evidence)));
    latestBrief = {
      prism_version: VERSION,
      artifact: "Analysis Brief",
      query,
      dataset: datasetMeta(),
      provider: activeProvider,
      method_version: METHOD_VERSION,
      classification: result.classification,
      answer: findings,
      citations: result.citations || [],
      evidence: result.evidence || [],
      assumptions: ["Only evidence available in the active browser workspace and governed browser-local records is eligible for citation.", "A citation indicates traceability to a PRISM evidence record; it does not by itself establish causal validity."],
      limitations: ["The static Copilot is a deterministic evidence composer, not a general-purpose language model.", "Evidence availability depends on which PRISM modules have been run or persisted in this browser.", "Material recommendations require accountable human review."],
      generated_at: new Date().toISOString(),
      uploaded_data_transmitted: false
    };
    const download = document.getElementById("downloadAnalysisBrief");
    if (download) download.disabled = false;
  }

  function focusEvidence(id) {
    if (!id) return;
    const candidates = [...document.querySelectorAll(".evidence-insight,.investigation-evidence,.driver-evidence,.strategy-card,.insight-item,.insight,article,p,li,tr")];
    const target = candidates.find((el) => safe(el.innerText || el.textContent).includes(id));
    if (!target) return;
    const view = target.closest(".view");
    if (view?.id) {
      const viewName = view.id.replace(/^view-/, "");
      document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v === view));
      document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === viewName));
    }
    target.scrollIntoView({behavior:"smooth", block:"center"});
  }

  function downloadBrief() {
    if (!latestBrief) return;
    const blob = new Blob([JSON.stringify(latestBrief, null, 2)], {type:"application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `PRISM_ANALYSIS_${slug(latestBrief.dataset.name)}_${stamp()}.json`;
    document.body.appendChild(a); a.click(); const url = a.href; a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function showCopilot() {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    document.getElementById("view-copilot")?.classList.add("active");
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === "copilot"));
    document.body.classList.remove("sidebar-open");
    document.getElementById("sidebar")?.setAttribute("aria-hidden", "true");
    document.getElementById("menuToggle")?.setAttribute("aria-expanded", "false");
    window.scrollTo({top:0, behavior:"smooth"});
    document.getElementById("copilotQuestion")?.focus({preventScroll:true});
  }

  function injectStyles() {
    if (document.getElementById("prismCopilotStyles")) return;
    const style = document.createElement("style");
    style.id = "prismCopilotStyles";
    style.textContent = `
      .copilot-shell{display:grid;gap:14px}.copilot-input{display:grid;gap:10px}.copilot-input textarea{width:100%;min-height:110px;resize:vertical}
      .copilot-actions,.copilot-suggestions,.copilot-citations,.copilot-result-head{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
      .copilot-suggestion,.copilot-citation{border:1px solid rgba(120,230,170,.22);background:rgba(120,230,170,.07);color:var(--accent);border-radius:8px;padding:7px 9px;font-size:11px;cursor:pointer}
      .copilot-citation{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.copilot-citation:hover,.copilot-suggestion:hover{background:rgba(120,230,170,.13)}
      .copilot-findings{display:grid;gap:8px;margin:12px 0}.copilot-guidance{padding-top:10px;border-top:1px solid var(--border)}
      #downloadAnalysisBrief:disabled{opacity:.45;cursor:not-allowed}
      @media(max-width:600px){.copilot-actions>*{width:100%}.copilot-suggestions{display:grid;grid-template-columns:1fr 1fr}.copilot-suggestion{min-height:42px}}
      @media(max-width:380px){.copilot-suggestions{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
  }

  function inject() {
    if (document.getElementById("view-copilot")) return;
    injectStyles();
    const quality = document.getElementById("view-quality");
    if (!quality) return;
    const section = document.createElement("section");
    section.id = "view-copilot";
    section.className = "view";
    section.innerHTML = `
      <div class="section-intro"><div><p class="eyebrow">ASK PRISM</p><h2>AI Analytical Copilot</h2><p>Ask a business or analytical question. The static edition answers only from traceable PRISM evidence already available in this browser and refuses unsupported claims.</p></div><button id="downloadAnalysisBrief" class="secondary-button" type="button" disabled>Download Analysis Brief</button></div>
      <article class="panel copilot-shell">
        <div class="copilot-input"><label for="copilotQuestion">Question</label><textarea id="copilotQuestion" placeholder="e.g. Why did margin change, what evidence supports the explanation, and what should we review next?"></textarea></div>
        <div class="copilot-suggestions" aria-label="Suggested questions">
          <button class="copilot-suggestion" type="button">Why did the KPI change?</button>
          <button class="copilot-suggestion" type="button">What does the evidence support?</button>
          <button class="copilot-suggestion" type="button">What strategy is currently proposed?</button>
          <button class="copilot-suggestion" type="button">Did the recorded decision meet its expected outcome?</button>
        </div>
        <div class="copilot-actions"><button id="askCopilot" class="primary-button" type="button">Ask PRISM</button><button id="clearCopilot" class="secondary-button" type="button">Clear</button><span id="copilotEvidenceCount" class="tag muted">0 evidence records available</span></div>
        <div id="copilotResult" class="insight-list"><div class="insight-item"><strong>Evidence-first by design</strong><p>Run PRISM analytical modules first. Copilot citations use existing EVD-* records; if supporting evidence is absent, PRISM refuses the answer rather than inventing one.</p></div></div>
      </article>
      <article class="panel"><div class="panel-heading"><div><p class="eyebrow">GUARDRAILS</p><h2>Copilot contract</h2></div></div><div class="two-column"><div class="insight-item"><strong>Grounded</strong><p>Answers must carry valid EVD-* citations from the active workspace or governed browser-local records.</p></div><div class="insight-item"><strong>Human accountable</strong><p>Recommendations remain decision support; approval and material action stay with accountable people.</p></div></div></article>`;
    quality.parentNode.insertBefore(section, quality);

    const side = document.querySelector('.nav-list .nav-item[data-view="quality"]');
    if (side) {
      const button = document.createElement("button");
      button.className = "nav-item";
      button.dataset.view = "copilot";
      button.type = "button";
      button.textContent = "AI Copilot";
      side.parentNode.insertBefore(button, side);
    }
    document.querySelectorAll('[data-view="copilot"]').forEach((button) => button.addEventListener("click", showCopilot));

    document.getElementById("askCopilot")?.addEventListener("click", async () => {
      const input = document.getElementById("copilotQuestion");
      const query = safe(input?.value);
      if (!query) { input?.focus(); return; }
      const result = await ask(query);
      renderResult(result, query);
    });
    document.getElementById("copilotQuestion")?.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") document.getElementById("askCopilot")?.click();
    });
    document.getElementById("clearCopilot")?.addEventListener("click", () => {
      latestBrief = null;
      const input = document.getElementById("copilotQuestion"); if (input) input.value = "";
      const result = document.getElementById("copilotResult"); if (result) result.innerHTML = '<div class="insight-item"><strong>Ready</strong><p>Ask a question grounded in evidence already produced by PRISM.</p></div>';
      const download = document.getElementById("downloadAnalysisBrief"); if (download) download.disabled = true;
    });
    document.getElementById("downloadAnalysisBrief")?.addEventListener("click", downloadBrief);
    document.querySelectorAll(".copilot-suggestion").forEach((button) => button.addEventListener("click", () => {
      const input = document.getElementById("copilotQuestion"); if (input) input.value = button.textContent.trim();
      document.getElementById("askCopilot")?.click();
    }));

    const count = document.getElementById("copilotEvidenceCount");
    const refreshCount = () => { if (count) { const n = collectEvidence().length; count.textContent = `${n} evidence record${n === 1 ? "" : "s"} available`; } };
    refreshCount();
    setTimeout(refreshCount, 500);
    setTimeout(refreshCount, 1600);
    const version = document.getElementById("versionLabel"); if (version) version.textContent = "v1.8.0 · GitHub Pages";
  }

  function registerProvider(name, adapter) {
    if (!name || name === PROVIDER || !adapter || typeof adapter.compose !== "function") throw new Error("Provider adapter must have a unique name and compose() function.");
    providers.set(String(name), adapter);
  }
  function setProvider(name) {
    if (name !== PROVIDER && !providers.has(name)) throw new Error("Unknown Copilot provider.");
    activeProvider = name;
  }

  window.PRISMCopilot = {ask, collectEvidence, registerProvider, setProvider, methodVersion:METHOD_VERSION, provider:() => activeProvider};
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", () => setTimeout(inject, 40)) : setTimeout(inject, 40);
})();