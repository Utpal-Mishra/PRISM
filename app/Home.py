from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.express as px
import streamlit as st

from app.components.filters import apply_sidebar_filters
from prism.config import settings
from prism.data.loader import load_sample_data, load_tabular_data
from prism.data.validator import validate_data
from prism.reporting.insights import generate_observations
from prism.reporting.metrics import (
    calculate_kpis,
    monthly_revenue,
    prepare_reporting_data,
    product_performance,
    region_performance,
)

st.set_page_config(page_title="PRISM", page_icon="◈", layout="wide")
st.title("PRISM")
st.caption("Product reporting intelligence for practical strategic decisions")

with st.sidebar:
    st.subheader("Data source")
    source = st.radio("Choose data", ["Sample data", "Upload file"], label_visibility="collapsed")
    uploaded = st.file_uploader("CSV or XLSX", type=["csv", "xlsx"]) if source == "Upload file" else None

try:
    raw = load_tabular_data(uploaded) if uploaded is not None else load_sample_data()
except (ValueError, OSError) as error:
    st.error(f"Unable to load data: {error}")
    st.stop()

result = validate_data(raw)
if result.errors:
    st.error("Data validation failed")
    for error in result.errors:
        st.write(f"- {error}")
    st.stop()

data = prepare_reporting_data(result.dataframe.dropna(subset=["order_date", "quantity", "unit_price"]))
filtered = apply_sidebar_filters(data)
kpis = calculate_kpis(filtered)

columns = st.columns(6)
columns[0].metric("Revenue", f"€{kpis['revenue']:,.0f}")
columns[1].metric("Orders", f"{kpis['orders']:,}")
columns[2].metric("Units", f"{kpis['units']:,}")
columns[3].metric("Customers", f"{kpis['customers']:,}")
columns[4].metric("Average order", f"€{kpis['aov']:,.0f}")
columns[5].metric("Data quality", f"{result.quality_score:.1f}%")

st.divider()
trend = monthly_revenue(filtered)
products = product_performance(filtered).head(10)
regions = region_performance(filtered)
left, right = st.columns([2, 1])
with left:
    st.subheader("Revenue trend")
    st.plotly_chart(
        px.line(trend, x="month", y="revenue", markers=True, labels={"month": "Month", "revenue": "Revenue (€)"}),
        use_container_width=True,
    )
with right:
    st.subheader("Regional performance")
    st.plotly_chart(
        px.bar(regions, x="revenue", y="region", orientation="h", labels={"revenue": "Revenue (€)"}),
        use_container_width=True,
    )

st.subheader("Top products")
st.plotly_chart(
    px.bar(products, x="product_name", y="revenue", hover_data=["category", "units", "orders"]),
    use_container_width=True,
)

st.subheader("What this means")
for observation in generate_observations(filtered):
    st.write(f"• {observation}")

with st.expander("Data quality details"):
    st.write(f"Rows loaded: {len(raw):,}")
    st.write(f"Rows analysed: {len(filtered):,}")
    for warning in result.warnings:
        st.warning(warning)
    if not result.warnings:
        st.success("No material data-quality warnings detected.")

st.download_button(
    "Download filtered data",
    filtered.to_csv(index=False).encode(),
    "prism_filtered_data.csv",
    "text/csv",
)
st.caption(f"{settings.app_name} v0.1.0 · Week 1 Reporting Foundation")
