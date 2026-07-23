# PRISM — Product Reporting Intelligence & Strategy Management

PRISM turns product reporting data into trusted KPIs, quality findings, and practical strategic observations.

## Current release — v0.2.0 Production-Readiness Foundation

- CSV/XLSX upload and built-in demonstration data
- Schema validation and data-quality scoring
- Executive KPIs and responsive filters
- Revenue, product, and regional reporting
- Rule-based strategic observations and CSV export
- Optional access-code authentication for controlled demos
- Settings and About pages
- Structured logging, privacy-conscious audit events, and optional Sentry reporting
- Tests, Ruff, pre-commit, GitHub Actions, Dependabot, Docker, and Streamlit configuration
- Standard pull-request workflow and generated GitHub release notes

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app/Home.py
```

## Required columns

`order_id`, `order_date`, `product_id`, `product_name`, `category`, `region`, `customer_id`, `quantity`, `unit_price`, `order_status`

Optional: `discount`.

## Environment variables

Copy `.env.example` to `.env` for local development. Never commit `.env` or `.streamlit/secrets.toml`.

```text
APP_ENV=production
ENABLE_DEMO_MODE=true
ENABLE_AUTHENTICATION=false
APP_ACCESS_CODE=
SENTRY_DSN=
```

The access-code gate is intended for demonstrations, not enterprise identity. Audit logs use ephemeral local storage on Streamlit Community Cloud. See [production-readiness boundaries](docs/production_readiness.md).

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

See [deployment instructions](docs/deployment.md). Merging a validated release into `main` automatically refreshes the connected Streamlit app.

## Release process

1. Build work on `agent/<scope>`.
2. Open a pull request into `develop` for integration.
3. Promote a tested release from `develop` into `main`.
4. Create a version tag such as `v0.2.0`; GitHub Actions generates the release notes.

## Branches

- `main`: deployable releases
- `develop`: integration
- `agent/production-readiness`: v0.2.0 implementation

## Documentation

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Deployment](docs/deployment.md)
- [Production readiness](docs/production_readiness.md)
- [Decisions](docs/decisions.md)
- [Changelog](CHANGELOG.md)

## Current limitations

PRISM currently uses in-memory uploaded or generated demonstration data. Prototype authentication and local audit storage must be replaced by enterprise identity and persistent infrastructure before confidential multi-user use. Forecasting and the remaining intelligence modules are scheduled for later releases.
