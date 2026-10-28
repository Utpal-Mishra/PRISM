# Changelog

## 1.11.0 — Enterprise P2 Governed Data & AI Control Plane

- Added enterprise `DATA-*` assets tied to governed P1 connector sources.
- Added explicit durable dataset materialisation jobs producing bounded, versioned, immutable `SNAP-*` records with classification, schema summary, SHA-256 content hash and provenance.
- Added PostgreSQL Row Level Security for P2 data assets, snapshots, Evidence Graph edges, Decision Cases and AI team runs.
- Added a PostgreSQL trigger that rejects snapshot updates while preserving governed retention/deletion.
- Added `EVD-DATA-*` metadata evidence without embedding raw materialised rows in evidence, job results or audit events.
- Added persisted shared Evidence Graph edges connecting connectors, data assets, snapshots, evidence, team runs, Decision Cases and human decisions.
- Added the first five Control Plane teams: Data, Analytics, Data Science, Strategy and Governance.
- Added deterministic business-question routing with classification-bounded evidence selection and explicit insufficient-evidence refusal.
- Added persisted `DC-*` Decision Cases and `AITeamRun` records with methods, limitations, linked `EVD-*` evidence and `causal-not-established` guardrails.
- Added Governance review-readiness checks and Manager/Admin approval before a Decision Case can be promoted to a `DEC-*` human decision.
- Added durable Decision Case/materialisation worker jobs with retries, terminal-state reconciliation and Prometheus counters.
- Added P2 lifecycle support for snapshot retention and explicit deletion of data assets/Decision Cases with dependent lineage cleanup.
- Added dedicated P2 regression tests for snapshot bounds/versioning, clearance filtering, five-team routing, refusal, reruns, evidence pinning and retention pointer repair.
- Extended CI and PostgreSQL disaster-recovery validation for P2 tables, contracts and snapshot immutability.
- Kept live external AI-provider invocation disabled in P2; provider egress remains governed by the P1 boundary for a later release.

## 1.10.0 — Enterprise P1 Scale & Reliability

- Added governed server-side HTTPS REST and read-only PostgreSQL connector execution with deployment egress allowlists, bounded extraction and redirect refusal.
- Added encrypted/versioned connector credentials, rotation/revocation and rejection of plaintext secret-like connector configuration.
- Added PostgreSQL-backed durable jobs with leases, retry budgets, `SKIP LOCKED` worker claims and connector-run retry/terminal status reconciliation.
- Added a dedicated enterprise worker service while keeping credentials/raw extracts out of the operational job payload.
- Added database-backed workspace write/job quotas with HTTP 429 and Retry-After semantics.
- Added Prometheus HTTP/latency/job/connector metrics, shared request correlation IDs and explicit initial SLO targets.
- Added checksum-verified PostgreSQL backup/restore scripts and an automated PostgreSQL 17 restore drill.
- Added tenant-scoped retention policies and Manager-requested/Admin-approved deletion workflows with tamper-evident completion audit.
- Added disabled-by-default governed AI-provider registration, encrypted credentials, provider egress allowlists and recorded purpose/data-policy requirements before enablement.
- Added bounded staging load-smoke tooling.
- Added Chromium desktop/mobile Playwright acceptance, npm audit and axe serious/critical accessibility gating; remediated keyboard/focus defects surfaced by the new gate.
- Added P1 regression coverage for connector boundaries, encrypted rotation, durable jobs, quotas, retention and AI-provider policies.
- Preserved the public GitHub Pages application as a browser-local demonstration rather than converting it into the confidential enterprise runtime.

## 1.9.0 — Enterprise P0 Foundation

- Added a separate authenticated PRISM Enterprise FastAPI runtime while preserving GitHub Pages as the public/browser-local demonstration surface.
- Added production OIDC/OAuth token verification with issuer/audience/time/sub validation and HTTPS-only discovery/JWKS endpoints.
- Added authoritative tenant, workspace, enterprise-user and membership persistence with server-side Viewer/Analyst/Manager/Admin RBAC and data-classification clearance enforcement.
- Added PostgreSQL production requirement, tenant/workspace transaction context and forced Row Level Security for governed tenant-scoped records.
- Added Alembic enterprise schema migration foundation for evidence, strategy, decision, outcome, encrypted-secret and audit records.
- Added HMAC-chained tamper-evident audit records plus PostgreSQL append-only protection.
- Added AES-256-GCM field encryption with key versioning and fail-closed production secret requirements.
- Added enterprise security middleware, dedicated non-root container packaging and a PostgreSQL-backed local enterprise deployment contract.
- Hardened browser-demo ingestion with upload size/shape/cell limits, bounded workbook parsing, CSV formula-injection neutralisation and an explicit confidential-data boundary.
- Added repository security ownership and vulnerability policy, CodeQL, dependency auditing, Bandit, committed-secret scanning and CycloneDX SBOM generation.
- Added enterprise P0 regression tests and upgraded vulnerable legacy/reference dependencies to security-compatible versions.
- Pinned GitHub workflow actions by immutable SHA and documented the required `main` repository protection ruleset as a release-blocking platform setting.

## 1.8.0 — AI Analytical Copilot

- Completed Day 15 of the PRISM enterprise Evidence-to-Strategy roadmap, closing the original programme at 15/15 stages.
- Added an evidence-first **AI Analytical Copilot** workspace that answers only from traceable PRISM evidence already available in the active browser workspace or governed browser-local records.
- Added deterministic intent routing across KPI movement/drivers, relationships, forecast, strategy, decisions, outcomes, data quality and governed definitions.
- Added strict `EVD-*` citation validation, evidence-count visibility and evidence navigation back to supporting workspace records when available.
- Added defensive refusal when PRISM lacks enough relevant traceable evidence instead of fabricating an answer.
- Added cross-module grounding from active analytical evidence plus persisted Strategy, Decision, Outcome, Registry and Governance records.
- Added a future provider-adapter contract; externally composed answers are accepted only when they return citations matching valid PRISM evidence IDs.
- Added explicit causal guardrails and human-accountability language to Copilot outputs.
- Added **Download Analysis Brief** using `PRISM_ANALYSIS_<DATASET>_<YYYYMMDD-HHMM>.json` with query, answer, citations, evidence snapshot, method, assumptions and limitations.
- Preserved the static-edition privacy boundary: Copilot runs locally by default and exports `uploaded_data_transmitted: false`.
- Extended CI to syntax-check and contract-test the Copilot module, export naming, evidence-first behaviour, causal language and local-first privacy assertion.

## 1.7.0 — Enterprise Governance

- Added Viewer, Analyst, Manager and Admin role simulation with explicit permission capabilities and approval-transition guardrails.
- Added accountable governance controls for asset, approval state, data classification, Restricted/PII handling basis, model/method intended use and risk tier.
- Added browser-local `AUD-*` audit events and `EVD-GOV-*` governance evidence with method, assumptions and limitations.
- Added explicit static-edition boundaries: simulated permissions are not SSO/RBAC, local audit history is not immutable, and classification metadata requires organisational policy validation.
- Added responsive desktop/mobile Enterprise Governance workspace and defensive refusal of unaccountable approvals or incomplete Restricted/PII handling metadata.
- Added **Download Audit Log** using `PRISM_AUDIT_<DATASET>_<YYYYMMDD-HHMM>.json` with controls, audit events, evidence/method metadata, limitations and local-first security assertions.
- Extended CI to validate governance syntax, role contract, approval controls, PII foundation, export naming, local persistence and non-causal language.

## 1.6.0 — Data Lineage

- Added a browser-local lineage engine that assembles governed `Source → Field → Metric → Evidence → Strategy → Decision` traceability from existing PRISM registry, strategy and decision records.
- Added an interactive responsive lineage workspace with selectable nodes, incoming/outgoing trace links and recorded metadata inspection.
- Added defensive refusal when governed registry metadata is unavailable; PRISM does not invent missing lineage.
- Added explicit provenance classification and limitations so recorded trace/support links are not presented as causal influence or semantic validation.
- Added **Download Lineage** using `PRISM_LINEAGE_<DATASET>_<YYYYMMDD-HHMM>.json` with graph, method, evidence, assumptions, limitations and local-first privacy metadata.
- Extended CI to validate lineage syntax, graph contract, upstream storage keys, export naming and non-causal language.

## 1.5.0 — Dataset & Metric Registry

- Added a browser-local governed registry for trusted datasets (`DS-*`) and metrics (`MET-*`).
- Added dataset description, accountable owner, steward, refresh cadence and certification metadata with defensive refusal of unaccountable records.
- Added metric business definition, documented formula, source fields, aliases, owner and certification metadata with minimum-definition validation.
- Added `EVD-REG-*` governance evidence containing method, assumptions and limitations; certification is governance metadata and is not represented as proof of analytical correctness or causality.
- Added a responsive desktop/mobile Registry workspace with browser-local persistence; the static registry is not represented as an enterprise system of record.
- Added **Download Registry** using `PRISM_REGISTRY_<DATASET>_<YYYYMMDD-HHMM>.json` with dataset, metric, evidence, method and governance metadata.
- Extended CI to validate Registry syntax, export naming, source-field metadata, accountability, local persistence and non-causal language.

## 1.4.0 — Enterprise Data Connectors Foundation

- Added a versioned connector adapter contract for Local file, SQL, REST API and cloud-file patterns.
- Added explicit Local vs Connected execution modes, browser-local non-secret configuration, refresh cadence, provenance and configuration-readiness health metadata.
- Added `EVD-CONN-*` configuration evidence with method, assumptions and limitations; connector readiness is not represented as remote availability or analytical evidence.
- Added secret redaction and explicit safeguards that the static edition neither persists/exports secrets nor transmits uploaded data.
- Added responsive desktop/mobile Data Connectors navigation and controls.
- Added **Download Connector Configuration** using `PRISM_CONNECTOR_<DATASET>_<YYYYMMDD-HHMM>.json`.

## 1.3.0 — Recommendation → Outcome Feedback Loop

- Added browser-local `OUT-*` reviews linked to `DEC-*`, `STR-*` and `EVD-*` traceability.
- Added expected-versus-actual KPI variance, explicit evaluation periods, bounded expectation-alignment scoring and domain-owner learning notes.
- Added `EVD-OUT-*` observation evidence and explicit `causal-not-established` limitations.
- Added **Download Outcome Review** using `PRISM_OUTCOME_<DATASET>_<YYYYMMDD-HHMM>.json`.

## 1.2.0 — Decision Register

- Added a browser-local Decision Register that converts a reviewed Strategy Engine 2.0 proposal into an accountable `DEC-*` organisational decision record.
- Requires a named owner, selected action and review date before a decision can be recorded; PRISM refuses unaccountable records.
- Preserves traceability through linked `STR-*` strategy and `EVD-*` evidence IDs, plus problem, hypothesis, confidence, risk and method metadata.
- Records alternatives considered, selected action, expected outcome/validation target, KPI to monitor, status and review date.
- Explicitly classifies records as `organisational decision record; human-approved action; causal-not-established`; expected outcomes are not treated as proof of causal impact.
- Persists up to 50 recent decisions in browser-local storage and provides a local clear action; uploaded datasets remain browser-local.
- Added responsive desktop/mobile Decision Register navigation, accountable-decision form and decision-memory cards.
- Added **Download Decision Record** JSON export using `PRISM_DECISION_<DATASET>_<YYYYMMDD-HHMM>.json` with dataset, strategy, evidence, method, assumptions, limitations and accountability metadata.
- Extended CI to syntax-check and contract-test Decision Register traceability, export naming, local persistence, owner requirement and non-causal language.

## 1.1.0 — Strategy Engine 2.0

- Replaced generic narrative strategy cards with structured, decision-ready strategy proposals.
- Added stable `STR-*` strategy IDs and linked `EVD-*` evidence IDs.
- Added explicit problem, evidence, hypothesis, recommended action, alternative, expected-impact statement, confidence, risk, cost/effort proxy, dependencies, KPI, owner, review date and approval status fields.
- Added human-accountability guardrails: unassigned owners are visibly flagged and proposals remain `Proposed — human review required`.
- Added explicit `decision-support synthesis; causal-not-established` classification and refuses to assert expected impact from observational evidence.
- Added defensive handling for insufficient records or unusable KPI fields.
- Added browser-local strategy persistence without transmitting uploaded dataset contents.
- Added responsive mobile controls and proposal cards.
- Added **Download Strategy Pack** JSON export using `PRISM_STRATEGY_<DATASET>_<YYYYMMDD-HHMM>.json`, including dataset, method, evidence, assumptions, limitations and accountability metadata.

## 1.0.0 — Scenario & What-If Studio

- Added a browser-local Scenario & What-If Studio for testing user-adjustable driver assumptions against selected KPIs.
- Added baseline vs scenario KPI comparison using a transparent single-driver linear response sensitivity model.
- Added approximate impact ranges, sample-size metadata and a risk indicator based on uncertainty relative to estimated impact.
- Added stable `SCN-*` scenario IDs and linked `EVD-*` evidence records with method, source fields, assumptions and limitations.
- Added explicit `scenario sensitivity; causal-not-established` classification; scenarios are not presented as causal intervention forecasts.
- Added browser-local save/compare support for up to 12 recent scenarios using localStorage.
- Added defensive states for insufficient paired observations and drivers with inadequate variation.
- Added responsive mobile Scenario navigation, controls, KPI cards and saved-scenario comparison table.
- Added **Download Scenario Comparison** JSON export using `PRISM_SCENARIO_<DATASET>_<YYYYMMDD-HHMM>.json` with dataset, scenario, evidence, uncertainty and method metadata.
- Preserved browser-local handling for uploaded data; the scenario module does not transmit dataset contents.

## 0.9.0 — Forecast Intelligence

- Upgraded the Forecast view from a single trend model to browser-local evidence-based model comparison.
- Added four transparent candidates: Seasonal naive, Drift, Linear trend, and Trend + seasonality.
- Added terminal holdout backtesting with MAE, RMSE, WAPE, MAPE where valid, and forecast bias.
- Added model selection using lowest holdout WAPE when scale-normalised error is valid, with MAE fallback and a visible selection rationale.
- Added approximate 95% planning ranges derived from holdout RMSE and widened by forecast horizon.
- Added stable `FCT-*` forecast IDs and linked `EVD-*` predictive-evidence records with methods, source fields, assumptions and limitations.
- Added explicit `predictive; causal-not-established` classification so forecast patterns are not presented as causal claims.
- Added defensive handling requiring at least 12 usable monthly observations for model comparison.
- Added responsive candidate-comparison tables and mobile download controls.
- Added **Download Forecast Pack** JSON export using `PRISM_FORECAST_<DATASET>_<YYYYMMDD-HHMM>.json` with dataset, model comparison, backtest metrics, uncertainty, evidence IDs and method metadata.
- Preserved browser-local handling for CSV/XLSX uploads; forecasting and export remain local in the static edition.
- Extended CI to syntax-check Forecast Intelligence and validate candidate methods, error metrics, export naming and non-causal language.

## 0.8.0 — Driver & Root-Cause Engine

- Added a browser-local driver analysis panel that explains where KPI movement is concentrated across business dimensions.
- Added ranked contribution analysis with slice delta and contribution share against the net KPI movement.
- Added a price-volume-interaction bridge when compatible quantity and unit-price fields are detected, with explicit warning that interaction is not pure product mix.
- Added latest-period IQR outlier screening and a standardised latest-change signal relative to recent period-to-period movement.
- Added stable `DRV-*` analysis IDs and linked `EVD-*` evidence records covering methods, source fields, calculations, assumptions and limitations.
- Added explicit `causal-not-established` classification throughout the UI and export so contribution is not presented as causal root-cause proof.