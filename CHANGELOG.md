# Changelog

## 0.3.0 — Enterprise Intelligence Foundation

- Reframed PRISM from a fixed sales reporting dashboard into a domain-agnostic reporting, analytics and data-strategy workspace.
- Converted the public application from a Streamlit runtime to a browser-native GitHub Pages application.
- Added root `index.html`, responsive enterprise CSS, client-side analytical engine, manifest and GitHub Pages fallback.
- Added local browser processing for CSV/XLSX uploads; no PRISM application server receives uploaded dataset contents in the static edition.
- Added generic dataset profiling, schema-role inference, quality scoring and anomaly screening.
- Added relationship discovery and segment performance analysis.
- Added transparent monthly forecasting with holdout backtesting and uncertainty ranges.
- Added browser-side regression/classification with baseline comparisons and driver importance.
- Added Strategy Studio recommendations tied to evidence and decision impact.
- Expanded the built-in dataset into a deterministic synthetic enterprise demonstration dataset.
- Kept the Python/Streamlit implementation as a legacy analytical reference while the static edition stabilises.
- Added static application syntax validation to CI.

## 0.2.0 — Production-Readiness Foundation

- CSV/XLSX upload and demonstration data.
- Schema validation and data-quality scoring.
- Executive KPIs, filters, reporting and strategic observations.
- Optional access-code gate, audit events and structured logging.
- Docker, CI, linting, testing and deployment documentation.
