# PRISM — Product Reporting Intelligence & Strategy Management

PRISM is an enterprise-oriented reporting, analytics and data-strategy workspace. The public application is **browser-native and deployable on GitHub Pages**: uploaded CSV/XLSX data is analysed locally in the user's browser without a Streamlit/Python server.

## Current release — v1.8.0 Evidence-First AI Analytical Copilot

- Static GitHub Pages application served from `index.html`
- Domain-agnostic CSV/XLSX upload with local browser processing
- Synthetic demonstration dataset enabled by default; no real company or customer data is bundled
- Automated data profiling, quality scoring, duplicate checks, column-role inference and anomaly screening
- Relationship discovery through numeric correlations and segment performance analysis
- Monthly forecasting with trend/seasonality, holdout backtesting and uncertainty ranges
- Browser-side predictive regression/classification with held-out evaluation, baseline comparison and driver importance
- Strategy Engine 2.0 that converts evidence into auditable proposals, with accountable Decision Register and Outcome Feedback
- Dataset & Metric Registry, Data Lineage and Enterprise Governance foundations
- Evidence-first AI Analytical Copilot with `EVD-*` citations, refusal on insufficient evidence and downloadable analysis briefs
- CSV exports for analysed data and generated strategy signals
- Responsive dark enterprise interface aligned with the shared **The Palm / NEXUS / XPLORE** product family
- Adaptive phone shell with off-canvas utilities, collapsible context, a persistent bottom analysis dock, safe-area support and responsive charts/tables


## Enterprise P0 foundation

PRISM now contains a separate enterprise server boundary under `enterprise/`. The public v1.8.0 GitHub Pages application remains the browser-local demonstration experience; it is **not** the confidential enterprise runtime.

The enterprise foundation provides OIDC authentication, authoritative tenant/workspace memberships, server-side RBAC/data clearance, PostgreSQL persistence with Row Level Security, governed evidence/decision records, tamper-evident audit history, AES-256-GCM field encryption, security middleware, schema migrations, container packaging and security CI/SBOM controls.

For enterprise setup and release gates, see:
- [Enterprise hosting](docs/enterprise_hosting.md)
- [Production readiness](docs/production_readiness.md)
- [Repository security controls](docs/repository_controls.md)

A production tenant still requires environment activation of an approved identity provider, managed PostgreSQL, HTTPS ingress, secret/KMS-backed keys and the documented GitHub `main` protection ruleset.

## Enterprise P1 scale & reliability

The enterprise runtime now adds the first operational scale layer above P0: governed HTTPS REST/PostgreSQL connectors, encrypted credential rotation, PostgreSQL-backed workers with leases/retries, distributed workspace quotas, Prometheus metrics/SLO targets, retention and approved deletion workflows, tested PostgreSQL backup/restore, governed AI-provider registration, and browser E2E/accessibility gates.

The public GitHub Pages app remains browser-local and does not become an enterprise data endpoint. P1 connector execution and future AI-provider egress live only behind the authenticated enterprise API/worker boundary.

Operational references:
- [Enterprise operations](docs/enterprise_operations.md)
- [Disaster recovery](docs/disaster_recovery.md)
- [Production readiness](docs/production_readiness.md)

Production still requires environment activation of managed PostgreSQL/PITR, approved OIDC, HTTPS ingress, secret/KMS injection, monitoring/alerts, exact egress allowlists, staging load measurement and the documented GitHub main protection ruleset.

## Shared visual language

PRISM uses the same dark-first product family as The Palm and NEXUS: green-black canvas, restrained glass/elevated surfaces, sage secondary text, green interaction states and a scarce lime accent for brand/high-value actions.

Canonical dark tokens include:

```text
Background  #07110d
Surface     #0b1712
Surface 2   #0e1d17
Border      #1e3229
Text        #edf7f1
Muted       #8fa39a
Green       #78e6aa
Green 2     #52d98d
Lime        #c8f56b
```

The browser charts are also routed through the shared palette so data visualisations do not drift back into a separate blue-themed product identity.

## Mobile experience

At phone widths, PRISM changes information architecture instead of merely scaling the desktop page. Dataset controls and privacy information live in an off-canvas drawer, the long product introduction collapses into the sticky top bar, and the six analytical views remain available from a Palm-inspired bottom dock. Cards, controls, tables and Plotly charts reflow across common phone widths and landscape orientation while respecting modern device safe areas.

The mobile shell deliberately preserves browser zoom and accessibility behaviour. Select controls use mobile-safe sizing, touch targets are at least approximately 44px, wide data tables remain horizontally scrollable with a sticky first column, and responsive chart resizing runs after view, viewport and orientation changes.

## Core workflow

```text
Upload / Synthetic Demo
    ↓
Profile & Validate
    ↓
Describe & Segment
    ↓
Discover Relationships & Exceptions
    ↓
Predict Outcomes + Forecast Time Series
    ↓
Translate Evidence into Strategy
    ↓
Record Decisions & Outcomes
    ↓
Govern Definitions, Lineage & Approvals
    ↓
Ask PRISM with Evidence Citations
    ↓
Export, Review, Learn & Iterate
```

PRISM is intentionally **decision-oriented** rather than dashboard-oriented: each analytical module should help answer what changed, what is related, what may happen next, what can be influenced, and what decision the organisation should evaluate.

## GitHub Pages deployment

The repository root contains the deployable static application:

```text
index.html
assets/styles.css
assets/mobile.css
assets/theme.js
assets/mobile.js
assets/app.js
assets/prism.svg
manifest.webmanifest
404.html
.nojekyll
```

GitHub repository settings:

```text
Settings → Pages
Source: Deploy from a branch
Branch: main
Folder: /(root)
```

After a validated release is merged to `main`, GitHub Pages publishes the application at:

```text
https://utpal-mishra.github.io/PRISM/
```

No build step, Python process, API server or Streamlit deployment is required for the public application.

## Supported input

Current browser input formats: CSV, XLSX and XLS. The XLSX reader and charting library are loaded from pinned CDN versions; CSV parsing and the analytical engine are implemented in the application itself.

PRISM does not require a fixed schema for its generic intelligence layer. It infers numeric, categorical, identifier and date/time fields from the uploaded file and activates analyses supported by the available evidence.

## Privacy model for the GitHub Pages edition

Uploaded files are read using browser File APIs and analysed in browser memory. PRISM does not send the uploaded dataset to a PRISM application server. This is a useful privacy property for the public static edition, but it is **not the same as enterprise security certification**.

Confidential enterprise use must use the separate authenticated PRISM Enterprise runtime. Its P0 security boundary now implements identity, tenant isolation, persistent governed storage, RBAC/data clearance, encryption and tamper-evident auditing; production activation still requires approved hosting, managed secrets/keys, repository protection, monitoring, retention controls and formal security review.

Predictive drivers and correlations are associations, not causal proof. Strategy signals are decision-support hypotheses and should be reviewed by accountable domain owners.

## Local static preview

From the repository root:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/`.

## Legacy Python implementation

The `app/` and `prism/` Python packages remain in the repository as the earlier Streamlit implementation and analytical reference while the browser-native edition stabilises. They are **not required by GitHub Pages** and can be retired or repurposed into future authenticated backend services later.

## Quality checks

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
node --check assets/theme.js
node --check assets/mobile.js
node --check assets/app.js
node --check assets/copilot.js
```

## Documentation

- [Architecture](docs/architecture.md)
- [Design system](docs/design_system.md)
- [GitHub Pages deployment](docs/deployment.md)
- [Data dictionary](docs/data_dictionary.md)
- [Production readiness](docs/production_readiness.md)
- [Changelog](CHANGELOG.md)


## AI Analytical Copilot

PRISM v1.8.0 completes the original 15-stage enterprise Evidence-to-Strategy roadmap with a browser-local analytical Copilot. The Copilot is intentionally not a generic chatbot: it composes answers from traceable PRISM evidence and requires valid `EVD-*` citations. If the current workspace does not contain sufficient relevant evidence, it refuses the question and directs the user to the analytical module that should be run first.

The static edition uses a deterministic local composer by default and does not transmit the uploaded dataset. A provider-adapter contract exists for future authenticated enterprise deployments, but provider output is accepted as grounded only when its citations map back to evidence already known by PRISM.
