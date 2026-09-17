# PRISM — 15-Day Enterprise Evidence-to-Strategy Roadmap

**Roadmap ID:** PRISM-RM-15D-20260909  
**Version:** 1.0  
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

### Objective
Create organisational memory for why important decisions were made.

### Delivered
- Accountable `DEC-*` records created from a reviewed Strategy Engine 2.0 proposal.
- Required decision owner, selected action and review date with refusal of unaccountable records.
- Linked `STR-*` strategy and `EVD-*` evidence IDs plus problem, hypothesis, confidence, risk and method context.
- Alternatives considered, selected action, expected outcome/validation target, KPI, status and review date.
- Browser-local persistence for up to 50 decision records and explicit local clear control.
- Explicit `organisational decision record; human-approved action; causal-not-established` classification and causal limitations.
- Responsive desktop/mobile Decision Register navigation, form and organisational-memory cards.
- **Download Decision Record** using `PRISM_DECISION_<DATASET>_<YYYYMMDD-HHMM>.json` with evidence, method, accountability, assumptions and limitations.

---
## Day 10 — Recommendation → Outcome Feedback Loop
**Status:** ☐ Planned

### Objective
Evaluate whether a recommendation or decision achieved the expected outcome.

### Build
Expected vs actual KPI, evaluation period, variance, transparent effectiveness score, learning metadata, and **Download Outcome Review**.

---
## Day 11 — Enterprise Data Connectors Foundation
**Status:** ☐ Planned

### Objective
Create an extensible connector architecture without compromising local-first operation.

### Build
Connector adapter contract, source configuration, mock SQL/REST/cloud-file patterns, local vs connected mode, health/refresh metadata and secret-free configuration export.

---
## Day 12 — Dataset & Metric Registry
**Status:** ☐ Planned

### Objective
Create controlled definitions for trusted datasets and KPIs.

### Build
Dataset ID/description/owner/steward/cadence/certification plus metric name/definition/formula/source fields/aliases and **Download Registry**.

---
## Day 13 — Data Lineage
**Status:** ☐ Planned

### Objective
Trace decision outputs through metrics, transformations and data sources.

### Build
Source → field → metric → evidence → strategy → decision graph, interactive lineage view and lineage JSON export.

---
## Day 14 — Enterprise Governance
**Status:** ☐ Planned

### Objective
Introduce the governance model required for eventual enterprise use.

### Build
Viewer/analyst/manager/admin roles, static permission simulation, approval states, audit schema, PII/data classification foundation, model-governance metadata and **Download Audit Log**.

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

## North-star experience
PRISM should answer with traceable evidence: What happened? Why? How certain? What next? What under alternatives? What should we do? Why? Who approved? Did it work? What did we learn?
