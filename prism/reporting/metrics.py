import pandas as pd


def prepare_reporting_data(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    cancelled = data["order_status"].astype(str).str.lower().eq("cancelled")
    data["revenue"] = data["quantity"] * data["unit_price"] * (1 - data["discount"])
    data.loc[cancelled, "revenue"] = 0.0
    data["month"] = data["order_date"].dt.to_period("M").dt.to_timestamp()
    return data


def calculate_kpis(df: pd.DataFrame) -> dict[str, float | int | str]:
    completed = ~df["order_status"].astype(str).str.lower().eq("cancelled")
    active = df.loc[completed]
    revenue = float(active["revenue"].sum())
    orders = int(active["order_id"].nunique())
    units = int(active["quantity"].sum())
    customers = int(active["customer_id"].nunique())
    return {
        "revenue": revenue,
        "orders": orders,
        "units": units,
        "customers": customers,
        "aov": revenue / orders if orders else 0.0,
    }


def monthly_revenue(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("month", as_index=False)["revenue"].sum().sort_values("month")


def product_performance(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["product_name", "category"], as_index=False)
        .agg(revenue=("revenue", "sum"), units=("quantity", "sum"), orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )


def region_performance(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("region", as_index=False)
        .agg(revenue=("revenue", "sum"), orders=("order_id", "nunique"))
        .sort_values("revenue", ascending=False)
    )
