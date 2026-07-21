import pandas as pd

from prism.data.validator import validate_data
from prism.reporting.metrics import calculate_kpis, prepare_reporting_data


def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "order_date": ["2026-01-01", "2026-01-02"],
            "product_id": ["P1", "P2"],
            "product_name": ["Mouse", "Keyboard"],
            "category": ["Accessories", "Accessories"],
            "region": ["Ireland", "Ireland"],
            "customer_id": ["C1", "C2"],
            "quantity": [2, 1],
            "unit_price": [50, 100],
            "discount": [0.1, 0],
            "order_status": ["Completed", "Cancelled"],
        }
    )


def test_validation_accepts_valid_data() -> None:
    result = validate_data(sample_df())
    assert not result.errors
    assert result.quality_score == 100.0


def test_cancelled_orders_do_not_add_revenue() -> None:
    data = prepare_reporting_data(validate_data(sample_df()).dataframe)
    kpis = calculate_kpis(data)
    assert kpis["revenue"] == 90.0
    assert kpis["orders"] == 1
