# Stage 12 — Dataset & Metric Registry

**Status:** Implemented on stage branch — 2026-09-20. Merge remains gated on CI and the required roadmap/changelog edits.

## Vertical slice
PRISM now provides a browser-local governed registry workspace at `registry.html` backed by `assets/registry.js`.

Dataset records include stable `DS-*` IDs, name, description, accountable owner, steward, refresh cadence, certification state, timestamp, and `EVD-REG-*` governance evidence. Dataset registration refuses records without owner and steward.

Metric records include stable `MET-*` IDs, business definition, documented formula, source fields, aliases, owner, certification state, timestamp, and `EVD-REG-*` governance evidence. Metric registration refuses incomplete name/definition/formula/source-field records.

Certification is explicitly governance metadata rather than proof of analytical validity. The static registry remains in browser `localStorage`; it is not presented as an enterprise system of record.

## Export
**Download Registry** creates `PRISM_REGISTRY_<DATASET>_<YYYYMMDD-HHMM>.json` with dataset and metric definitions, evidence/method metadata, governance assertions, assumptions and limitations.

## Validation
CI syntax-checks `assets/registry.js` and contract-checks the responsive registry page, export label/naming, source fields, certification, owner/steward, browser-local persistence and non-causal evidence language.

## Architecture fit
This stage governs definitions used by the existing Data → Evidence → Explanation → Prediction → Scenario → Strategy → Decision → Action → Outcome → Learning chain and prepares Day 13 lineage to connect source fields and governed metrics to downstream evidence and decisions.
