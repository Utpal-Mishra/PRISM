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
Strategy Studio
  ├─ Prioritised signals
  ├─ Evidence statements
  ├─ Recommended actions
  └─ Decision-impact framing
        ↓
CSV export
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
