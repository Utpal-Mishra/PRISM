# Changelog

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
