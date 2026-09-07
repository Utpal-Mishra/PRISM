import numpy as np
import pandas as pd


def strongest_correlations(
    df: pd.DataFrame,
    limit: int = 12,
    minimum_absolute_correlation: float = 0.15,
) -> pd.DataFrame:
    numeric = df.select_dtypes(include="number").copy()
    numeric = numeric.loc[:, numeric.nunique(dropna=True) > 1]
    if numeric.shape[1] < 2:
        return pd.DataFrame(
            columns=["variable_a", "variable_b", "correlation", "direction", "strength"]
        )

    correlation = numeric.corr(method="pearson")
    rows: list[dict[str, object]] = []
    for index, column_a in enumerate(correlation.columns):
        for column_b in correlation.columns[index + 1 :]:
            value = correlation.loc[column_a, column_b]
            if pd.isna(value) or abs(float(value)) < minimum_absolute_correlation:
                continue
            absolute = abs(float(value))
            if absolute >= 0.7:
                strength = "Strong"
            elif absolute >= 0.4:
                strength = "Moderate"
            else:
                strength = "Weak"
            rows.append(
                {
                    "variable_a": column_a,
                    "variable_b": column_b,
                    "correlation": round(float(value), 3),
                    "direction": "Positive" if value >= 0 else "Negative",
                    "strength": strength,
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["absolute_correlation"] = result["correlation"].abs()
    result = result.sort_values("absolute_correlation", ascending=False).head(limit)
    return result.drop(columns="absolute_correlation").reset_index(drop=True)


def segment_performance(
    df: pd.DataFrame,
    segment_column: str,
    metric_column: str,
    aggregation: str = "sum",
    limit: int = 15,
) -> pd.DataFrame:
    if segment_column not in df or metric_column not in df:
        return pd.DataFrame(columns=[segment_column, "value", "share_pct"])

    working = df[[segment_column, metric_column]].copy()
    working[metric_column] = pd.to_numeric(working[metric_column], errors="coerce")
    working = working.dropna(subset=[segment_column, metric_column])
    if working.empty:
        return pd.DataFrame(columns=[segment_column, "value", "share_pct"])

    grouped = working.groupby(segment_column, dropna=False)[metric_column]
    if aggregation == "mean":
        result = grouped.mean().sort_values(ascending=False)
    elif aggregation == "median":
        result = grouped.median().sort_values(ascending=False)
    else:
        result = grouped.sum().sort_values(ascending=False)

    result = result.head(limit).rename("value").reset_index()
    total = float(result["value"].sum())
    if aggregation == "sum" and total != 0:
        result["share_pct"] = 100.0 * result["value"] / total
    else:
        result["share_pct"] = np.nan
    return result


def anomaly_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for column in df.select_dtypes(include="number").columns:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(series) < 8 or series.nunique() <= 1:
            continue
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        if iqr <= 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        count = int(((series < lower) | (series > upper)).sum())
        rows.append(
            {
                "column": column,
                "outliers": count,
                "outlier_pct": round(100.0 * count / len(series), 2),
                "lower_bound": round(lower, 3),
                "upper_bound": round(upper, 3),
            }
        )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values("outlier_pct", ascending=False).reset_index(drop=True)
