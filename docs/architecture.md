# PRISM Architecture

## Product goal

PRISM is designed as an enterprise reporting and data-strategy platform rather than a fixed dashboard. The system should accept governed business data, understand the structure available, apply the analytical methods that the evidence supports, and turn the resulting signals into decision-ready outputs.

## v0.3 logical flow

```text
Data source
  ├─ Synthetic PRISM demo
  └─ CSV / XLSX upload
        ↓
Ingestion layer
        ↓
Schema and quality profiler
  ├─ Numeric / categorical / date inference
  ├─ Missingness / duplicates / constants
  ├─ Identifier detection
  └─ Outlier screening
        ↓
Reporting and analytics layer
  ├─ Descriptive metrics
  ├─ Domain-specific reporting when recognised
  ├─ Segment performance
  ├─ Relationship discovery
  └─ Exception analysis
        ↓
Foresight layer
  ├─ Predictive regression / classification
  ├─ Holdout evaluation + baselines
  ├─ Driver importance
  ├─ Time-series aggregation
  └─ Forecast + backtest + uncertainty
        ↓
Strategy Studio
  ├─ Prioritised signals
  ├─ Evidence statements
  ├─ Recommended actions
  └─ Decision-impact framing
        ↓
Export / audit / governance
```

## Design principles

1. **Domain-agnostic first.** Do not require one business schema for generic intelligence.
2. **Evidence before recommendations.** Every recommendation should point to a measurable signal.
3. **Prediction is not causation.** Driver importance and correlations remain exploratory until validated.
4. **Backtest forecasts.** Forecast quality must be visible rather than implied.
5. **Synthetic by default.** Public demonstrations bundle only dummy data.
6. **Govern production data.** Confidential use requires enterprise identity, storage, lineage, tenant isolation, retention and security controls beyond the public prototype.
7. **Composable intelligence.** Reporting, forecasting, prediction and strategy should remain modular services rather than UI-only logic.

## Enterprise target architecture

The Streamlit application is currently the product shell. A production enterprise edition should progressively separate the layers:

- UI: web application / workspace
- API: authenticated analytics and strategy services
- Compute: queued profiling, modelling and forecasting jobs
- Storage: governed warehouse/lakehouse plus metadata catalogue
- Model registry: versioned forecasting and predictive artefacts
- Governance: RBAC/SSO, audit logs, lineage, retention and policy enforcement
- Integrations: Snowflake, Databricks, BigQuery, Redshift, Fabric, S3/Blob, APIs and BI tools
- Outputs: dashboards, scheduled reports, alerts, strategy briefs and machine-readable recommendations
