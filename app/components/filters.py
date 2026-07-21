import pandas as pd
import streamlit as st


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    categories = st.sidebar.multiselect("Category", sorted(df["category"].dropna().unique()))
    regions = st.sidebar.multiselect("Region", sorted(df["region"].dropna().unique()))
    products = st.sidebar.multiselect("Product", sorted(df["product_name"].dropna().unique()))
    minimum = df["order_date"].min().date()
    maximum = df["order_date"].max().date()
    dates = st.sidebar.date_input("Date range", (minimum, maximum), min_value=minimum, max_value=maximum)

    output = df.copy()
    if categories:
        output = output[output["category"].isin(categories)]
    if regions:
        output = output[output["region"].isin(regions)]
    if products:
        output = output[output["product_name"].isin(products)]
    if isinstance(dates, tuple) and len(dates) == 2:
        output = output[output["order_date"].dt.date.between(dates[0], dates[1])]
    return output
