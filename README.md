# PRISM — Product Reporting Intelligence & Strategy Management

PRISM is an enterprise-oriented reporting, analytics and data-strategy workspace. It turns uploaded tabular data into structured evidence, relationships, forecasts, predictive signals and practical strategy recommendations.

## Current release candidate — v0.3.0 Enterprise Intelligence Foundation

- Domain-agnostic CSV/XLSX upload: PRISM profiles the uploaded schema instead of requiring a sales-only structure
- Synthetic demonstration dataset enabled by default; no real company or customer data is bundled
- Automated data profiling, quality scoring, duplicate checks, column-role inference and anomaly screening
- Relationship discovery through numeric correlations and segment performance analysis
- Monthly forecasting with transparent trend + seasonality, holdout backtesting and uncertainty ranges
- Predictive regression/classification with held-out evaluation, baseline comparison and driver importance
- Strategy Studio that converts evidence into prioritised recommendations and decision-impact statements
- Existing sales/order KPIs remain available when PRISM recognises the original reporting schema
- CSV exports for analysed data and generated strategy signals
- Optional access-code authentication, structured logging and privacy-conscious audit events
- Tests, Ruff, pre-commit, GitHub Actions, Dependabot, Docker and Streamlit configuration

## Core workflow

```text
Upload / Demo
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

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app/Home.py
```

## Supported input

Current input formats: CSV, XLSX and XLS.

PRISM v0.3 does not require a fixed schema for its generic intelligence layer. It infers numeric, categorical, identifier and date/time fields from the uploaded file. Business-specific reporting modules can activate when a recognised schema is available.

## Safety and enterprise boundary

The built-in demo is synthetic. Uploaded files are analysed in the active Streamlit session, but the public/demo deployment must **not** be treated as a confidential enterprise data platform. Enterprise production use still requires organisation-grade identity, encryption, persistent governed storage, tenant isolation, retention controls, secrets management, data lineage, role-based access, monitoring and approved deployment infrastructure.

Predictive drivers and correlations are associations, not causal proof. Strategy signals are decision-support hypotheses and should be reviewed by accountable domain owners.

## Environment variables

Copy `.env.example` to `.env` for local development. Never commit `.env` or `.streamlit/secrets.toml`.

```text
APP_ENV=production
ENABLE_DEMO_MODE=true
ENABLE_AUTHENTICATION=false
APP_ACCESS_CODE=
SENTRY_DSN=
```

## Quality checks

```bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit run --all-files
ruff check .
pytest -q
```

## Deployment

Deploy on Streamlit Community Cloud using:

```text
Repository: Utpal-Mishra/PRISM
Branch: main
Main file: app/Home.py
```

See [deployment instructions](docs/deployment.md). A validated v0.3 release should be promoted through the normal branch/release workflow before it reaches `main`.

## Documentation

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Deployment](docs/deployment.md)
- [Production readiness](docs/production_readiness.md)
- [Changelog](CHANGELOG.md)
