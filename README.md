# PRISM — Product Reporting Intelligence & Strategy Management

PRISM is an enterprise-oriented reporting, analytics and data-strategy workspace. The public application is **browser-native and deployable on GitHub Pages**: uploaded CSV/XLSX data is analysed locally in the user's browser without a Streamlit/Python server.

## Current release candidate — v0.3.3 Adaptive Phone Experience

- Static GitHub Pages application served from `index.html`
- Domain-agnostic CSV/XLSX upload with local browser processing
- Synthetic demonstration dataset enabled by default; no real company or customer data is bundled
- Automated data profiling, quality scoring, duplicate checks, column-role inference and anomaly screening
- Relationship discovery through numeric correlations and segment performance analysis
- Monthly forecasting with trend/seasonality, holdout backtesting and uncertainty ranges
- Browser-side predictive regression/classification with held-out evaluation, baseline comparison and driver importance
- Strategy Studio that converts evidence into prioritised recommendations and decision-impact statements
- CSV exports for analysed data and generated strategy signals
- Responsive dark enterprise interface aligned with the shared **The Palm / NEXUS / XPLORE** product family
- Adaptive phone shell with off-canvas utilities, collapsible context, a persistent bottom analysis dock, safe-area support and responsive charts/tables

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
Translate Evidence into Strategy Signals
    ↓
Export, Govern, Monitor & Iterate
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

Confidential enterprise use still requires organisation-grade identity, approved hosting, encryption, governed persistent storage, tenant isolation, retention controls, secrets management, data lineage, role-based access, monitoring and formal security review.

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
```

## Documentation

- [Architecture](docs/architecture.md)
- [Design system](docs/design_system.md)
- [GitHub Pages deployment](docs/deployment.md)
- [Data dictionary](docs/data_dictionary.md)
- [Production readiness](docs/production_readiness.md)
- [Changelog](CHANGELOG.md)
