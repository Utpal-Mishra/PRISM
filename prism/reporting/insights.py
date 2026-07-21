import pandas as pd


def generate_observations(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["No data is available for the selected filters."]
    observations: list[str] = []
    products = df.groupby("product_name")["revenue"].sum().sort_values(ascending=False)
    regions = df.groupby("region")["revenue"].sum().sort_values(ascending=False)
    if not products.empty:
        share = products.iloc[0] / max(products.sum(), 1) * 100
        observations.append(
            f"{products.index[0]} leads product revenue and contributes {share:.1f}% of the selected total."
        )
    if not regions.empty:
        observations.append(f"{regions.index[0]} is the strongest region by revenue.")
    monthly = df.groupby("month")["revenue"].sum().sort_index()
    if len(monthly) >= 2 and monthly.iloc[-2] != 0:
        growth = (monthly.iloc[-1] / monthly.iloc[-2] - 1) * 100
        direction = "increased" if growth >= 0 else "decreased"
        observations.append(
            f"Revenue {direction} by {abs(growth):.1f}% in the latest month versus the previous month."
        )
    cancellation_rate = df["order_status"].astype(str).str.lower().eq("cancelled").mean() * 100
    if cancellation_rate > 5:
        observations.append(
            f"Cancellation rate is {cancellation_rate:.1f}%; investigate product, region, and fulfilment drivers."
        )
    return observations
