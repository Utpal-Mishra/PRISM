# PRISM — 15-Day Enterprise Evidence-to-Strategy Roadmap

**Roadmap ID:** PRISM-RM-15D-20260909  
**Version:** 1.0  
**Start date:** 2026-09-09  
**Target end date:** 2026-09-23  
**Product direction:** Data → Evidence → Explanation → Prediction → Scenario → Strategy → Decision → Action → Outcome → Learning

## Roadmap intent

This sprint is designed to move PRISM from a browser-native analytical workspace toward an evidence-backed enterprise decision-intelligence platform. Each day delivers a practical vertical slice, not a claim of full production maturity. Every stage must preserve the core principles below.

### Non-negotiable product principles

1. **No recommendation without evidence.**
2. **Traceability by default:** raw data → method → finding → recommendation → decision → outcome.
3. **Statistical honesty:** descriptive, associative, predictive and causal evidence must be clearly distinguished.
4. **Enterprise usefulness over dashboard volume:** fewer, better decision objects instead of more charts.
5. **Explainability:** important outputs must show why they were generated and what assumptions were used.
6. **Human accountability:** PRISM supports decisions; accountable owners approve material actions.
7. **Local-first static edition:** uploaded datasets remain browser-local unless a future connector is explicitly configured.
8. **Responsive experience:** each stage must be usable on desktop and phone.

## Download and export standard

Every stage that creates a material analytical output must expose a clearly labelled download action. Labels should describe the artifact, for example **Download Evidence Pack**, **Download Forecast Pack**, **Download Strategy Pack**, or **Download Decision Record**.

File naming convention:

`PRISM_<MODULE>_<DATASET>_<YYYYMMDD-HHMM>.<ext>`

Examples:

- `PRISM_EVIDENCE_sales-demo_20260909-0830.json`
- `PRISM_FORECAST_sales-demo_20260914-0830.csv`
- `PRISM_STRATEGY_sales-demo_20260916-0830.json`
- `PRISM_DECISION_sales-demo_20260917-0830.json`

Where relevant, exported artifacts should include:

- PRISM version
- generated timestamp
- dataset name / dataset ID
- active filters
- analytical method
- evidence IDs
- assumptions
- confidence / uncertainty
- source fields
- model or calculation version

## Definition of Done for every daily stage

A stage is complete only when the daily implementation includes, where applicable:

- working UI vertical slice
- underlying analytical logic or structured data object
- explainability / evidence metadata
- mobile-responsive behavior
- labelled downloadable output
- defensive handling for insufficient data
- repository documentation update
- changelog entry
- lightweight validation / CI compatibility
- stage status updated in this roadmap

---

## Day 1 — Evidence Foundation

**Status:** ☑ Completed — 2026-09-09

### Objective
Make every material analytical finding traceable to the dataset, fields, filters, calculation and confidence context that produced it.

### Build
- Introduce a reusable `EvidenceRecord` structure.
- Assign stable evidence IDs.
- Add clickable evidence details to overview insights.
- Capture source fields, row count, filters, method, assumptions and quality score.
- Add **Download Evidence Pack**.

### UX target
Insight → Evidence → Method → Source → Confidence.

### Success criteria
A user can inspect and export the evidence behind an overview insight without manually reconstructing the calculation.

---

## Day 2 — Enterprise Semantic Layer

**Status:** ☐ Planned

### Objective
Move PRISM from column-type detection to business meaning detection.

### Build
- Infer measures, dimensions, identifiers, time fields and probable business entities.
- Detect likely KPI concepts such as revenue, units, margin, cost, spend, inventory and returns.
- Create a Business Model panel.
- Allow user correction of inferred roles in-browser.
- Export the semantic model.

### UX target
Replace “19 columns” as the only structural interpretation with business-readable concepts and entity relationships.

---

## Day 3 — Automated Analytical Investigation

**Status:** ☐ Planned

### Objective
Automatically investigate meaningful KPI movement instead of requiring the user to decide every drill-down.

### Build
- Detect notable KPI changes.
- Investigate by time, category and segment.
- Rank contributing slices.
- Produce an investigation path and supporting evidence IDs.
- Add **Download Investigation Pack**.

### UX target
KPI change → where → what segment → main contributor → supporting signals.

---

## Day 4 — Statistical Evidence Layer

**Status:** ☐ Planned

### Objective
Add method-appropriate statistical evidence and clearly label evidence strength.

### Build
- Pearson / Spearman association.
- Difference testing where valid.
- Chi-square for categorical association where valid.
- Confidence intervals and sample-size reporting.
- Evidence classification: descriptive / association / predictive / causal-not-established.
- Export statistical test details.

### UX target
Every statistical statement explains method, sample size, effect, uncertainty and limitations.

---

## Day 5 — Driver & Root-Cause Engine

**Status:** ☐ Planned

### Objective
Explain what contributed to a KPI movement.

### Build
- Contribution analysis by dimensions.
- Price / volume / mix style decomposition when required fields are available.
- Outlier and change-point supporting signals.
- Driver ranking with contribution share.
- Add **Download Driver Analysis**.

### UX target
Show a ranked “what moved the KPI” explanation, not merely correlations.

---

## Day 6 — Forecast Intelligence

**Status:** ☐ Planned

### Objective
Upgrade forecasting from a single method to evidence-based model selection and backtesting.

### Build
- Baseline and candidate forecast methods suitable for browser execution.
- Holdout backtesting.
- MAE, RMSE, WAPE/MAPE where valid, bias and prediction intervals.
- Model-selection rationale.
- Add **Download Forecast Pack**.

### UX target
Forecast + uncertainty + backtest + why this model was selected.

---

## Day 7 — Scenario & What-If Studio

**Status:** ☐ Planned

### Objective
Let users test alternative assumptions and compare decision scenarios.

### Build
- User-adjustable assumptions for selected drivers.
- Baseline vs scenario comparison.
- Impact range and risk indicator.
- Scenario save / compare support in browser state.
- Add **Download Scenario Comparison**.

### UX target
“What if X changes?” becomes an evidence-backed comparison rather than a manual spreadsheet exercise.

---

## Day 8 — Strategy Engine 2.0

**Status:** ☐ Planned

### Objective
Convert analytical findings into structured, decision-ready strategy objects.

### Build
A strategy object should contain:
- problem
- evidence
- hypothesis
- recommended action
- alternatives
- expected impact
- confidence
- risk
- cost / effort proxy
- dependency
- KPI to monitor
- owner
- review date

Add **Download Strategy Pack**.

### UX target
Recommendations become auditable strategy proposals, not generic narrative cards.

---

## Day 9 — Decision Register

**Status:** ☐ Planned

### Objective
Create organisational memory for why important decisions were made.

### Build
- Decision ID.
- Decision owner.
- linked evidence and strategy IDs.
- alternatives considered.
- selected action.
- expected outcome.
- status and review date.
- local browser persistence for static edition.
- Add **Download Decision Record**.

### UX target
A user can later answer “why did we make this decision?” with a structured record.

---

## Day 10 — Recommendation → Outcome Feedback Loop

**Status:** ☐ Planned

### Objective
Evaluate whether a recommendation or decision actually achieved the expected outcome.

### Build
- Expected vs actual KPI outcome.
- elapsed evaluation period.
- outcome variance.
- strategy effectiveness score with transparent formula.
- learning note / model feedback metadata.
- Add **Download Outcome Review**.

### UX target
PRISM starts learning from the effectiveness of previous decisions rather than only generating new analysis.

---

## Day 11 — Enterprise Data Connectors Foundation

**Status:** ☐ Planned

### Objective
Create an extensible connector architecture without compromising the local-first static edition.

### Build
- Connector interface / adapter contract.
- configuration model for sources.
- mock adapters for SQL warehouse / REST / cloud-file patterns.
- clear distinction between local upload and connected mode.
- connector health / last refresh metadata.
- export connector configuration template excluding secrets.

### UX target
A future Snowflake, Databricks, BigQuery, SAP or Salesforce integration can plug into a common interface.

---

## Day 12 — Dataset & Metric Registry

**Status:** ☐ Planned

### Objective
Create controlled definitions for trusted datasets and KPIs.

### Build
- Dataset ID and description.
- owner / steward.
- refresh cadence.
- certified flag.
- metric name, definition, formula and source fields.
- semantic aliases.
- Add **Download Registry**.

### UX target
Users can distinguish a certified KPI from an inferred or exploratory measure.

---

## Day 13 — Data Lineage

**Status:** ☐ Planned

### Objective
Show how a decision output traces back through metrics, transformations and data sources.

### Build
- lineage graph data structure.
- source → field → metric → evidence → strategy → decision links.
- interactive lineage view for available in-browser artifacts.
- export lineage JSON.

### UX target
Click a KPI or recommendation and see where it came from.

---

## Day 14 — Enterprise Governance

**Status:** ☐ Planned

### Objective
Introduce the governance model required for eventual enterprise use.

### Build
- role model: viewer / analyst / manager / admin.
- permission matrix as a static-edition governance simulation.
- approval state for strategies and decisions.
- audit-event schema.
- data classification / PII flagging foundation.
- model-governance metadata.
- Add **Download Audit Log**.

### UX target
Separate analysis, approval and administration responsibilities even before full SSO/RBAC infrastructure is introduced.

---

## Day 15 — AI Analytical Copilot

**Status:** ☐ Planned

### Objective
Add an AI-ready analytical interaction layer that is grounded in PRISM evidence rather than free-form unsupported claims.

### Build
- evidence-first query contract.
- question templates such as “why did X change?”, “what are the main risks?”, “what supports recommendation Y?”.
- deterministic local answer composer for the static edition using available PRISM evidence objects.
- provider adapter interface for a future approved LLM connection.
- citation of evidence IDs in generated answers.
- refusal / limitation behavior when evidence is insufficient.
- Add **Download Analysis Brief**.

### UX target
Natural-language analysis that can always point back to PRISM evidence and methods.

---

# Post-15-day continuation

After the 15-day vertical-slice sprint, the next major programme should be production hardening rather than uncontrolled feature expansion:

- analytical validation against benchmark datasets
- accessibility and performance testing
- larger-file / worker-thread architecture
- persisted backend and workspace model
- real enterprise connectors
- SSO and production RBAC
- secret management
- encrypted storage
- observability
- versioned model registry
- approval workflows
- agentic analyst / strategy / validation roles
- formal security review

## North-star experience

PRISM should eventually answer, with traceable evidence:

1. What happened?
2. Why did it happen?
3. How certain are we?
4. What is likely to happen next?
5. What happens under alternative decisions?
6. What should we do?
7. Why is that recommendation justified?
8. Who approved the decision?
9. Did the action work?
10. What should the organisation learn from the result?
