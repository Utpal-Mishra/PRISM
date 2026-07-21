from dataclasses import dataclass

import pandas as pd

REQUIRED_COLUMNS = {
    "order_id",
    "order_date",
    "product_id",
    "product_name",
    "category",
    "region",
    "customer_id",
    "quantity",
    "unit_price",
    "order_status",
}


@dataclass
class ValidationResult:
    dataframe: pd.DataFrame
    errors: list[str]
    warnings: list[str]
    quality_score: float


def validate_data(df: pd.DataFrame) -> ValidationResult:
    data = df.copy()
    errors: list[str] = []
    warnings: list[str] = []
    missing = sorted(REQUIRED_COLUMNS - set(data.columns))
    if missing:
        errors.append(f"Missing required columns: {', '.join(missing)}")
        return ValidationResult(data, errors, warnings, 0.0)

    data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
    for column in ["quantity", "unit_price"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if "discount" not in data:
        data["discount"] = 0.0
    data["discount"] = pd.to_numeric(data["discount"], errors="coerce").fillna(0).clip(0, 1)

    invalid_dates = int(data["order_date"].isna().sum())
    invalid_numeric = int(data[["quantity", "unit_price"]].isna().any(axis=1).sum())
    duplicate_orders = int(data["order_id"].duplicated().sum())
    if invalid_dates:
        warnings.append(f"{invalid_dates} rows have invalid dates.")
    if invalid_numeric:
        warnings.append(f"{invalid_numeric} rows have invalid quantity or price.")
    if duplicate_orders:
        warnings.append(f"{duplicate_orders} duplicate order IDs detected.")
    if (data["quantity"] <= 0).any():
        warnings.append("Non-positive quantities detected.")
    if (data["unit_price"] < 0).any():
        warnings.append("Negative unit prices detected.")

    critical_cells = len(data) * len(REQUIRED_COLUMNS)
    missing_cells = int(data[list(REQUIRED_COLUMNS)].isna().sum().sum())
    penalty = missing_cells + invalid_dates + invalid_numeric + duplicate_orders
    score = max(0.0, 100.0 * (1 - penalty / max(critical_cells, 1)))
    return ValidationResult(data, errors, warnings, round(score, 1))
