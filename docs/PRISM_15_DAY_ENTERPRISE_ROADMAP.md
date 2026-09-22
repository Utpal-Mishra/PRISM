# PRISM — 15-Day Enterprise Evidence-to-Strategy Roadmap

**Roadmap ID:** PRISM-RM-15D-20260909  
**Version:** 1.1  
**Start date:** 2026-09-09  
**Target end date:** 2026-09-23  
**Product direction:** Data → Evidence → Explanation → Prediction → Scenario → Strategy → Decision → Action → Outcome → Learning

## Roadmap intent
This sprint moves PRISM from a browser-native analytical workspace toward an evidence-backed enterprise decision-intelligence platform. Each day delivers a practical vertical slice, not a claim of full production maturity.

### Non-negotiable product principles
1. **No recommendation without evidence.**
2. **Traceability by default:** raw data → method → finding → recommendation → decision → outcome.
3. **Statistical honesty:** descriptive, associative, predictive and causal evidence must be clearly distinguished.
4. **Enterprise usefulness over dashboard volume.**
5. **Explainability:** important outputs show why they were generated and what assumptions were used.
6. **Human accountability:** accountable owners approve material actions.
7. **Local-first static edition:** uploaded datasets remain browser-local unless a connector is explicitly configured.
8. **Responsive experience:** each stage is usable on desktop and phone.

## Download and export standard
Every material output exposes a clearly labelled download action using `PRISM_<MODULE>_<DATASET>_<YYYYMMDD-HHMM>.<ext>` and includes dataset/method/evidence/assumption/uncertainty metadata where relevant.

## Definition of Done
Working UI vertical slice; analytical/structured object; explainability/evidence metadata; responsive behavior; labelled export; insufficient-data handling; documentation/changelog; lightweight validation; roadmap status update.

---
## Day 1 — Evidence Foundation
**Status:** ☑ Completed — 2026-09-09
## Day 2 — Enterprise Semantic Layer
**Status:** ☑ Completed — 2026-09-10
## Day 3 — Automated Analytical Investigation
**Status:** ☑ Completed — 2026-09-11
## Day 4 — Statistical Evidence Layer
**Status:** ☑ Completed — 2026-09-12
## Day 5 — Driver & Root-Cause Engine
**Status:** ☑ Completed — 2026-09-13
## Day 6 — Forecast Intelligence
**Status:** ☑ Completed — 2026-09-14
## Day 7 — Scenario & What-If Studio
**Status:** ☑ Completed — 2026-09-15
## Day 8 — Strategy Engine 2.0
**Status:** ☑ Completed — 2026-09-16
## Day 9 — Decision Register
**Status:** ☑ Completed — 2026-09-17
## Day 10 — Recommendation → Outcome Feedback Loop
**Status:** ☑ Completed — 2026-09-18

---
## Day 11 — Enterprise Data Connectors Foundation
**Status:** ☑ Completed — 2026-09-19

### Objective
Create an extensible connector architecture without compromising local-first operation.

### Delivered
- Versioned connector adapter contract covering Local file, SQL, REST API and cloud-file patterns.
- Explicit **Local** vs **Connected** execution mode labels; uploaded data remains browser-local unless an explicit runtime is configured.
- Browser-local non-secret source configuration and refresh cadence metadata.
- Configuration-readiness health state that does not pretend to test remote availability in the static edition.
- Provenance metadata, last-checked timestamp and `EVD-CONN-*` configuration evidence with method, assumptions and limitations.
- Secret-denylist redaction plus explicit `secrets_exported: false`, `secrets_persisted: false`, and `uploaded_data_transmitted: false` metadata.
- Responsive desktop/mobile Data Connectors navigation and controls.
- **Download Connector Configuration** using `PRISM_CONNECTOR_<DATASET>_<YYYYMMDD-HHMM>.json`.

---
## Day 12 — Dataset & Metric Registry
**Status:** ☑ Completed — 2026-09-20

### Objective
Create controlled definitions for trusted datasets and KPIs.

### Delivered
- Browser-local governed `DS-*` dataset definitions with description, accountable owner, steward, refresh cadence and certification.
- Governed `MET-*` metric definitions with business definition, documented formula, source fields, aliases, owner and certification.
- Defensive validation that refuses incomplete or unaccountable registry records.
- `EVD-REG-*` governance evidence with method, assumptions and limitations; certification is governance metadata, not proof of analytical correctness or causality.
- Responsive desktop/mobile Registry workspace with browser-local persistence; the static registry is not represented as an enterprise system of record.
- **Download Registry** using `PRISM_REGISTRY_<DATASET>_<YYYYMMDD-HHMM>.json` with dataset, metric, evidence, method and governance metadata.

---
## Day 13 — Data Lineage
**Status:** ☑ Completed — 2026-09-21

### Objective
Trace decision outputs through metrics, transformations and data sources.

### Delivered
- Deterministic browser-local `Source → Field → Metric → Evidence → Strategy → Decision` graph assembled from governed registry, strategy and decision records.
- Interactive responsive lineage workspace with selectable nodes, metadata inspection and incoming/outgoing trace links.
- Defensive refusal when governed registry metadata is absent; missing lineage is shown as incomplete rather than invented.
- Explicit provenance/support classification and limitations so trace links are not represented as causal influence or semantic validation.
- Local-first privacy metadata with no uploaded-data transmission in the static edition.
- **Download Lineage** using `PRISM_LINEAGE_<DATASET>_<YYYYMMDD-HHMM>.json` with graph, method, evidence, assumptions and limitations.

---
## Day 14 — Enterprise Governance
**Status:** ☑ Completed — 2026-09-22

### Objective
Introduce the governance model required for eventual enterprise use.

### Delivered
- Viewer, Analyst, Manager and Admin role simulation with explicit permission capabilities.
- Approval-state guardrails that reserve approve/reject transitions for Manager/Admin roles and require an accountable actor.
- Data-classification foundation covering Public, Internal, Confidential and Restricted / PII, with mandatory handling/lawful-basis note for Restricted / PII records.
- Model-governance metadata covering model/method, intended use, risk tier and mandatory human approval.
- Browser-local `AUD-*` audit events and `EVD-GOV-*` governance evidence with method, assumptions and limitations.
- Explicit static-edition boundaries: role simulation is not production RBAC; local audit events are not immutable; governance metadata is not analytical or causal proof.
- Responsive desktop/mobile Governance workspace with defensive validation and local-only persistence.
- **Download Audit Log** using `PRISM_AUDIT_<DATASET>_<YYYYMMDD-HHMM>.json` with governance controls, audit events, evidence/method metadata and local-first security assertions.

---
## Day 15 — AI Analytical Copilot
**Status:** ☐ Planned

### Objective
Add an AI-ready analytical interaction layer grounded in PRISM evidence rather than unsupported claims.

### Build
Evidence-first query contract, deterministic local answer composer, future provider adapter, evidence-ID citations, insufficient-evidence refusal and **Download Analysis Brief**.

---
# Post-15-day continuation
Production hardening: benchmark validation, accessibility/performance, worker architecture, persisted backend/workspaces, real connectors, SSO/RBAC, secrets, encryption, observability, model registry, approvals, validation agents and formal security review.

## Later enterprise release — AI Team Orchestration
**Status:** ☐ Future backlog — target after the governed enterprise foundation is established (v2.x direction)

### Objective
Evolve PRISM from a single analytical copilot into an evidence-grounded AI operating model that assembles the right specialist intelligence team for a business question, while preserving human accountability and PRISM's evidence-first architecture.

### AI Control Plane
Users should ask a business question rather than manually choosing agents. The PRISM control plane will interpret intent, decompose the problem, select the required AI teams, coordinate shared context, enforce evidence requirements, synthesise outputs and route material conclusions through governance and human review.

### First five core AI teams
1. **Data Team** — profiling, cleaning, transformation, schema mapping and data-quality assessment.
2. **Analytics Team** — KPI analysis, segmentation, statistical investigation, exception analysis and evidence-backed explanation.
3. **Data Science Team** — forecasting, predictive modelling, anomaly detection, simulation and optimisation support.
4. **Strategy Team** — scenario interpretation, strategic alternatives, structured recommendations and decision-support synthesis.
5. **Governance Team** — evidence validation, lineage, model-risk checks, assumptions, limitations, policy controls and approval readiness.

Each team may contain specialist roles coordinated by a team lead rather than relying on one general-purpose agent.

### Later specialist AI teams
After the core five teams demonstrate reliable evidence-grounded collaboration, expand the operating model with **Database, Business, Finance, Operations, Product, Development and Marketing** teams. These teams should use the same semantic layer, registries, lineage, evidence IDs, governance rules and decision records rather than creating isolated agent silos.

### Shared Evidence Graph
All AI-team findings must reference the shared evidence system. Evidence objects should connect source data, fields, methods, calculations, assumptions, uncertainty, findings, strategies, decisions and outcomes so that a recommendation can always be traced back to the analytical basis that supports it.

Expected relationship:
`Source → Field → Metric → EVD-* → Analysis → STR-* → Decision → Outcome → Learning`

### Decision Case format
PRISM should be able to persist a complete cross-team investigation as a `DC-*` Decision Case containing the business question, participating AI teams, linked evidence, analyses, models, scenarios, alternatives, strategy proposals, risks, decision owner, approval state, review date, expected outcome, observed outcome and lessons learned.

### Dynamic AI task forces
For cross-functional questions, PRISM may assemble temporary task forces from specialist roles rather than requiring permanent workflows. Example: a market-launch question could combine market, finance, customer, supply-chain, sustainability, risk and strategy specialists while retaining one evidence chain and one Decision Case.

### Outcome learning loop
AI-team recommendations should not terminate at recommendation generation. Linked Decision Cases should compare expected versus observed outcomes and feed validated learning back into future investigations, while clearly separating historical evidence from new predictions.

### Enterprise guardrails
- No AI team may present unsupported claims as evidence.
- Descriptive, associative, predictive and causal conclusions remain explicitly distinguished.
- Material recommendations remain human-approved.
- Cross-team outputs must preserve source, method, assumption and uncertainty metadata.
- PRISM remains the evidence and decision-intelligence layer; execution into operational systems is approval-gated and connector-mediated rather than silently autonomous.
- Specialist teams must share governed semantic definitions instead of creating competing KPI definitions.

### North-star AI-team experience
`Business Question → PRISM Control Plane → Specialist AI Teams → Shared Evidence Graph → Governance Review → Decision Case → Human Decision → Outcome Tracking → Learning`

## North-star experience
PRISM should answer with traceable evidence: What happened? Why? How certain? What next? What under alternatives? What should we do? Why? Who approved? Did it work? What did we learn?