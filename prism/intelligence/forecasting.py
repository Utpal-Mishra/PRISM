from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error


@dataclass(frozen=True)
class ForecastResult:
    history: pd.DataFrame
    forecast: pd.DataFrame
    projected_change_pct: float
    backtest_mae: float | None
    backtest_mape: float | None
    trend: str
    history_points: int


def _features(index: np.ndarray, dates: pd.Series) -> np.ndarray:
    month = pd.to_datetime(dates).dt.month.to_numpy(dtype=float)
    sin_month = np.sin(2 * np.pi * month / 12.0)
    cos_month = np.cos(2 * np.pi * month / 12.0)
    return np.column_stack([index, sin_month, cos_month])


def build_monthly_series(
    df: pd.DataFrame,
    date_column: str,
    value_column: str,
    aggregation: str = "sum",
) -> pd.DataFrame:
    working = df[[date_column, value_column]].copy()
    working[date_column] = pd.to_datetime(working[date_column], errors="coerce")
    working[value_column] = pd.to_numeric(working[value_column], errors="coerce")
    working = working.dropna()
    if working.empty:
        return pd.DataFrame(columns=["date", "value"])

    working["date"] = working[date_column].dt.to_period("M").dt.to_timestamp()
    grouped = working.groupby("date")[value_column]
    if aggregation == "mean":
        values = grouped.mean()
    elif aggregation == "median":
        values = grouped.median()
    else:
        values = grouped.sum()

    series = values.sort_index().rename("value").reset_index()
    if len(series) > 1:
        full_dates = pd.date_range(series["date"].min(), series["date"].max(), freq="MS")
        series = series.set_index("date").reindex(full_dates)
        series.index.name = "date"
        if aggregation == "sum":
            series["value"] = series["value"].fillna(0.0)
        else:
            series["value"] = series["value"].interpolate(limit_direction="both")
        series = series.reset_index()
    return series


def forecast_monthly_series(series: pd.DataFrame, periods: int = 6) -> ForecastResult:
    clean = series.dropna(subset=["date", "value"]).copy()
    if len(clean) < 6:
        raise ValueError("At least six monthly observations are required for forecasting.")

    clean["date"] = pd.to_datetime(clean["date"])
    clean["value"] = pd.to_numeric(clean["value"], errors="coerce")
    clean = clean.dropna(subset=["value"]).sort_values("date").reset_index(drop=True)

    index = np.arange(len(clean), dtype=float)
    features = _features(index, clean["date"])
    target = clean["value"].to_numpy(dtype=float)

    backtest_mae: float | None = None
    backtest_mape: float | None = None
    holdout = min(max(2, len(clean) // 5), 6)
    if len(clean) - holdout >= 4:
        model = LinearRegression()
        model.fit(features[:-holdout], target[:-holdout])
        predicted = model.predict(features[-holdout:])
        actual = target[-holdout:]
        backtest_mae = float(mean_absolute_error(actual, predicted))
        non_zero = np.abs(actual) > 1e-9
        if non_zero.any():
            backtest_mape = float(
                np.mean(np.abs((actual[non_zero] - predicted[non_zero]) / actual[non_zero]))
                * 100.0
            )

    model = LinearRegression()
    model.fit(features, target)
    fitted = model.predict(features)
    residual_std = float(np.std(target - fitted, ddof=1)) if len(clean) > 3 else 0.0

    future_dates = pd.date_range(
        clean["date"].max() + pd.offsets.MonthBegin(1),
        periods=periods,
        freq="MS",
    )
    future_index = np.arange(len(clean), len(clean) + periods, dtype=float)
    future_features = _features(future_index, pd.Series(future_dates))
    predicted_future = model.predict(future_features)

    lower = predicted_future - (1.96 * residual_std)
    upper = predicted_future + (1.96 * residual_std)
    forecast = pd.DataFrame(
        {
            "date": future_dates,
            "forecast": predicted_future,
            "lower": lower,
            "upper": upper,
        }
    )

    baseline = float(target[-min(3, len(target)) :].mean())
    future_level = float(predicted_future[-min(3, len(predicted_future)) :].mean())
    if abs(baseline) <= 1e-9:
        projected_change = 0.0
    else:
        projected_change = 100.0 * (future_level - baseline) / abs(baseline)

    if projected_change > 3:
        trend = "Growing"
    elif projected_change < -3:
        trend = "Declining"
    else:
        trend = "Stable"

    history = clean.rename(columns={"value": "actual"})[["date", "actual"]]
    return ForecastResult(
        history=history,
        forecast=forecast,
        projected_change_pct=round(float(projected_change), 1),
        backtest_mae=None if backtest_mae is None else round(backtest_mae, 3),
        backtest_mape=None if backtest_mape is None else round(backtest_mape, 1),
        trend=trend,
        history_points=len(clean),
    )
