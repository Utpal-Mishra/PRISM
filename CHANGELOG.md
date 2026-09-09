# Changelog

## 0.4.0 — Evidence Foundation

- Added stable evidence IDs and structured evidence records for Executive Overview findings.
- Added inspectable evidence details covering dataset identity, source fields, row count, method, calculation context, assumptions, confidence basis and limitations.
- Added a clearly labelled **Download Evidence Pack** JSON export with the naming convention `PRISM_EVIDENCE_<DATASET>_<YYYYMMDD-HHMM>.json`.
- Added descriptive vs association evidence labels and explicit non-causal limitations for correlation findings.
- Preserved browser-local processing for uploaded datasets; evidence generation and export remain client-side.
- Added responsive evidence metadata layouts for phone and desktop views.
- Kept defensive handling for unavailable evidence and unsupported analytical certainty.


## 0.3.4 — Compact Mobile KPI Overview

- Reworked the six Executive Overview KPI cards into a compact 3 × 2 grid on standard phone widths.
- Added a 2 × 3 fallback for very narrow devices below 341px so values remain readable.
- Reduced KPI card height, padding and mobile typography to surface analytical content sooner.
- Replaced long KPI helper text with concise mobile labels: Records, Fields, Quality, Measures, Time and Segments.
- Added a subtle accent treatment to Data Quality while leaving desktop and downstream analytical metric grids unchanged.

## 0.3.3 — Adaptive Phone Experience

- Added a persistent Palm-style mobile bottom dock for one-tap access to Overview, Relationships, Forecast, Predict, Strategy and Data Quality.
- Added `viewport-fit=cover` and safe-area-aware spacing for modern iPhone and Android devices, including gesture/navigation areas.
- Improved narrow-screen responsiveness across KPI cards, panels, controls, strategy cards, status elements and phone-sized typography.
- Added 44px+ touch targets and 16px mobile select controls to reduce accidental taps and prevent unwanted iOS form zoom.
- Improved mobile data tables with momentum scrolling, a sticky first column and better narrow-width handling.
- Added Plotly chart resize handling for viewport changes, orientation changes and view transitions.
- Improved landscape-phone behaviour and extra-small device handling down to approximately 320px widths.
- Removed the timed mobile drawer auto-close so navigation remains under explicit user control.
- Expanded CI validation for the adaptive mobile dock, safe-area CSS and responsive chart handling.

## 0.3.2 — Mobile App-Shell Experience

- Replaced the stacked mobile sidebar with an off-canvas navigation drawer opened from a top-left menu control.
- Added automatic sidebar dismissal after navigation, outside tap, Escape, file selection, or a short period of inactivity.
- Kept `ENTERPRISE REPORTING, ANALYTICS & DATA STRATEGY` persistently visible in the mobile top bar.
- Moved the large introduction, supporting copy and runtime status into an accessible slide-down disclosure on mobile.
- Improved touch target sizes, mobile controls, dataset banner layout, KPI responsiveness, chart sizing and horizontally scrollable tables.
- Added safe-area handling for modern phones and reduced-motion support for the new navigation transitions.
- Added CI validation for the mobile CSS and JavaScript assets.

## 0.3.1 — Shared Product Design System

- Aligned PRISM with the visual language used across The Palm, NEXUS and related portfolio products.
- Standardised the dark green base (`#07110d`), enterprise surfaces, sage text, green (`#78e6aa`) and lime (`#c8f56b`) accents.
- Updated navigation, upload controls, KPI cards, panels, tables, inputs, strategy cards and buttons to the shared product treatment.
- Added a browser chart-theme adapter so Plotly visuals use the same product palette.
- Updated the PRISM icon, browser/PWA theme colours and legacy Streamlit theme for consistency.
- Added CI checks for the shared design tokens and chart-theme JavaScript.

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
