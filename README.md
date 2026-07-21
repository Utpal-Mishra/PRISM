# PRISM — Product Reporting Intelligence & Strategy Management

PRISM turns product reporting data into trusted KPIs, quality findings, and practical strategic observations.

## Week 1 — Reporting Foundation

- CSV/XLSX upload and built-in sample data
- Schema validation and data-quality scoring
- Executive KPIs and responsive filters
- Revenue, product, and regional reporting
- Rule-based strategic observations
- CSV export
- Tests, Ruff, GitHub Actions, Docker, and Streamlit configuration

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

## Quality checks

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

## Deployment

Deploy on Streamlit Community Cloud using `app/Home.py` as the entry point. See [deployment instructions](docs/deployment.md).

## Branches

- `main`: deployable releases
- `develop`: integration
- `agent/week-1-reporting-foundation`: Week 1 implementation

## Current limitations

Week 1 uses in-memory uploaded or generated sample data. Authentication, persistent storage, forecasting, and AI recommendations are scheduled for later releases.
