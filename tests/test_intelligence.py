import pandas as pd

from prism.data.loader import load_sample_data
from prism.intelligence.forecasting import build_monthly_series, forecast_monthly_series
from prism.intelligence.prediction import train_predictive_model
from prism.intelligence.profile import profile_dataset
from prism.intelligence.relationships import strongest_correlations


def test_profile_detects_core_roles() -> None:
    data = load_sample_data(120)
    profile = profile_dataset(data)
    assert profile.rows == 120
    assert "order_date" in profile.date_columns
    assert "quantity" in profile.numeric_columns
    assert profile.quality_score > 95


def test_relationships_return_numeric_pairs() -> None:
    data = pd.DataFrame(
        {
            "a": range(1, 31),
            "b": [value * 2 for value in range(1, 31)],
            "category": ["x"] * 30,
        }
    )
    relationships = strongest_correlations(data)
    assert not relationships.empty
    assert relationships.iloc[0]["correlation"] == 1.0


def test_forecast_produces_future_periods() -> None:
    data = load_sample_data(700)
    monthly = build_monthly_series(data, "order_date", "quantity", "sum")
    result = forecast_monthly_series(monthly, periods=4)
    assert len(result.forecast) == 4
    assert result.history_points >= 6


def test_prediction_returns_evaluation_and_drivers() -> None:
    data = load_sample_data(300)
    result = train_predictive_model(
        data,
        "customer_satisfaction",
        ["lead_time_days", "marketing_spend", "quantity", "region", "channel"],
    )
    assert result.task == "Regression"
    assert result.test_rows > 0
    assert not result.feature_importance.empty
