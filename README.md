# PRISM — Product Reporting Intelligence & Strategy Management

PRISM transforms product reporting data into trusted KPIs, data-quality findings, and practical business observations.

## Week 1 release: v0.1.0 Reporting Foundation

### Included
- CSV/XLSX upload and sample-data mode
- Schema validation and data-quality scoring
- Executive KPI overview
- Product, category, region, and date filters
- Revenue trend, product performance, and regional performance charts
- Rule-based strategic observations
- Downloadable filtered data
- Unit tests, Ruff checks, GitHub Actions, Docker, and Streamlit deployment configuration

## Architecture

```text
Streamlit UI -> data loader/validator -> reporting engine -> insights -> exports
```

## Local setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app/Home.py
```

## Required input columns

`order_id`, `order_date`, `product_id`, `product_name`, `category`, `region`, `customer_id`, `quantity`, `unit_price`, `order_status`

Optional: `discount`, `cost_per_unit`, `returned`.

## Environment variables

See `.env.example`. Never commit `.env` or `.streamlit/secrets.toml`.

## Testing and quality

```bash
pytest -q
ruff check .
```

## Docker

```bash
docker build -t prism:v0.1.0 .
docker run -p 8501:8501 --env-file .env prism:v0.1.0
```

## Deployment

The repository is prepared for Streamlit Community Cloud. Select `app/Home.py` as the entry point and add secrets through the platform settings. See `docs/deployment.md`.

## Branch strategy

- `main`: deployable releases
- `develop`: integration branch
- `agent/week-1-reporting-foundation`: Week 1 implementation

## Documentation

- [Architecture](docs/architecture.md)
- [Data dictionary](docs/data_dictionary.md)
- [Deployment](docs/deployment.md)
- [Decisions](docs/decisions.md)
- [Changelog](CHANGELOG.md)

## Limitations

Week 1 uses uploaded or sample files and in-memory processing. Authentication, persistent database storage, forecasting, and AI recommendations are intentionally deferred.
