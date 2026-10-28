# PRISM Architecture

## Product goal

PRISM is designed as an enterprise reporting and data-strategy platform rather than a fixed dashboard. It should accept governed business data, understand the available structure, apply analytical methods supported by the evidence, and convert the resulting signals into decision-ready outputs.

## GitHub Pages edition — browser-native architecture

The public PRISM application is a static web application. GitHub Pages serves files; all user-data processing happens inside the browser.

```text
GitHub Pages
  └─ index.html + CSS + JavaScript
        ↓
Browser File API
  ├─ Synthetic PRISM demo
  ├─ CSV upload
  └─ XLSX / XLS upload
        ↓
Client-side ingestion
        ↓
Schema and quality profiler
  ├─ Numeric / categorical / date inference
  ├─ Missingness / duplicates / constants
  ├─ Identifier detection
  └─ IQR outlier screening
        ↓
Browser analytics layer
  ├─ Descriptive metrics
  ├─ Segment performance
  ├─ Pearson relationship discovery
  └─ Exception analysis
        ↓
Browser foresight layer
  ├─ Ridge-style numerical regression
  ├─ Centroid classification
  ├─ Held-out evaluation + baselines
  ├─ Driver importance
  ├─ Monthly time-series aggregation
  └─ Trend / seasonal forecast + backtest + uncertainty
        ↓
Evidence / decision layer
  ├─ Strategy Engine 2.0 (STR-*)
  ├─ Decision Register (DEC-*)
  ├─ Outcome Feedback (OUT-*)
  ├─ Dataset & Metric Registry
  ├─ Data Lineage
  └─ Enterprise Governance metadata
        ↓
AI Analytical Copilot
  ├─ Evidence-first question routing
  ├─ EVD-* citation validation
  ├─ Deterministic local answer composer
  ├─ Insufficient-evidence refusal
  └─ Future provider-adapter contract
        ↓
Governed JSON / CSV exports
```

The public edition does not require a Python process, Streamlit runtime or application server.

## Design principles

1. **Domain-agnostic first.** Do not require one business schema for generic intelligence.
2. **Local data processing for the public edition.** User-uploaded datasets stay in browser memory rather than being posted to a PRISM server.
3. **Evidence before recommendations.** Every recommendation should point to a measurable signal.
4. **Prediction is not causation.** Driver importance and correlations remain exploratory until validated.
5. **Backtest forecasts.** Forecast quality must be visible rather than implied.
6. **Synthetic by default.** Public demonstrations bundle only generated dummy data.
7. **Progressive enterprise separation.** Browser-native analytics is appropriate for the public portfolio/product demo; confidential multi-user enterprise deployment needs authenticated services and governed infrastructure.

## Enterprise target architecture

The GitHub Pages application is the public/product demonstration shell. A production enterprise edition should progressively add server-side governed services without discarding the browser experience:

- UI: authenticated web workspace derived from the current static interface
- API: analytics, strategy, metadata and workflow services
- Compute: queued profiling, modelling, forecasting and scenario jobs
- Storage: governed warehouse/lakehouse plus metadata catalogue
- Model registry: versioned forecasting and predictive artefacts
- Governance: RBAC/SSO, audit logs, lineage, retention and policy enforcement
- Integrations: Snowflake, Databricks, BigQuery, Redshift, Fabric, S3/Blob, APIs and BI tools
- Outputs: dashboards, scheduled reports, alerts, strategy briefs and machine-readable recommendations

The legacy Python modules can later become reusable backend services where heavier computation, persistent state, enterprise connectors or governed models are required.


## Enterprise P2 — governed data and AI Control Plane

P2 adds the first server-side decision-intelligence orchestration layer above P0/P1.

```text
Business question
      ↓
Authenticated PRISM Enterprise API
      ↓
DC-* Decision Case
      ↓
Durable decision_case_analyze job
      ↓
PRISM Control Plane
  ├─ Data Team
  ├─ Analytics Team
  ├─ Data Science Team
  ├─ Strategy Team
  └─ Governance Team
      ↓
Clearance-bounded EVD-* evidence
      ↓
Shared Evidence Graph
      ↓
Governance review-readiness
      ↓
Manager/Admin review
      ↓
Optional promotion to DEC-* human decision
```

The Control Plane in P2 is deterministic and evidence-grounded. It routes work and organises existing PRISM evidence; it does not create independent facts and it does not invoke an external AI provider.

P2 also introduces explicit governed data materialisation:

```text
Governed connector
      ↓
DATA-* asset
      ↓
dataset_materialize worker job
      ↓
bounded connector read
      ↓
immutable SNAP-* version
      ↓
EVD-DATA-* metadata evidence
      ↓
Evidence Graph
```

Snapshot rows are stored only after explicit materialisation. Raw rows are not placed in job results, audit events or `EVD-DATA-*` evidence payloads. PostgreSQL RLS protects P2 tenant-scoped records and a database trigger rejects snapshot updates; retention/deletion may still remove data according to policy.

## AI Copilot boundary

The v1.8.0 static Copilot is deliberately evidence-bound. It does not act as a general-purpose chatbot and does not silently transmit uploaded data. The default composer runs in-browser and may use only evidence present in the active PRISM workspace or governed records persisted in browser-local storage. Answers must cite valid `EVD-*` identifiers; unsupported questions are refused.

A future provider adapter may connect a governed model service, but provider output remains subject to the same evidence-citation validation before PRISM accepts it as grounded.

## AI-team orchestration roadmap

P2 now implements the governed Control Plane foundation for the Data, Analytics, Data Science, Strategy and Governance teams, together with shared Evidence Graph links and Decision Cases. Later v2.x work can connect approved model providers through the P1 provider boundary and expand to Database, Finance, Business, Operations, Product, Development and Marketing teams. All later teams must continue to share the same semantic definitions, Evidence Graph, Decision Cases, governance controls and human approval boundary rather than operating as isolated agents.
