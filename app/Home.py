import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st

from prism.auth import require_access
from prism.config import settings
from prism.data.loader import load_sample_data, load_tabular_data
from prism.data.validator import REQUIRED_COLUMNS, validate_data
from prism.intelligence.forecasting import build_monthly_series, forecast_monthly_series
from prism.intelligence.prediction import PredictionResult, train_predictive_model
from prism.intelligence.profile import column_inventory, profile_dataset
from prism.intelligence.relationships import (
    anomaly_summary,
    segment_performance,
    strongest_correlations,
)
from prism.intelligence.strategy import build_strategy_signals
from prism.observability import configure_logging, record_audit_event
from prism.reporting.metrics import calculate_kpis, prepare_reporting_data
from prism.ui.theme import apply_theme, theme_selector

st.set_page_config(page_title="PRISM", page_icon="◈", layout="wide")
logger = configure_logging()
session_id = st.session_state.setdefault("session_id", str(uuid.uuid4()))
require_access(session_id)


def enrich_analysis_frame(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    if {"quantity", "unit_price"}.issubset(data.columns):
        quantity = pd.to_numeric(data["quantity"], errors="coerce")
        price = pd.to_numeric(data["unit_price"], errors="coerce")
        data["gross_value"] = quantity * price
        if "discount" in data:
            discount = pd.to_numeric(data["discount"], errors="coerce").fillna(0).clip(0, 1)
            data["net_value"] = data["gross_value"] * (1 - discount)
        if "unit_cost" in data:
            unit_cost = pd.to_numeric(data["unit_cost"], errors="coerce")
            data["gross_margin"] = data.get("net_value", data["gross_value"]) - (
                quantity * unit_cost
            )
    return data


with st.sidebar:
    st.subheader("PRISM Workspace")
    theme = theme_selector("prism_theme")
    source = st.radio(
        "Data source",
        ["Synthetic demonstration data", "Upload file"],
        label_visibility="collapsed",
    )
    uploaded = None
    if source == "Upload file":
        uploaded = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx", "xls"])
        st.caption(
            "Files are analysed in-session. Do not upload confidential data to a public demo."
        )
    st.divider()
    st.caption("Pipeline")
    st.caption("Profile → Relate → Predict → Forecast → Strategise → Export")
    st.caption(f"Version {settings.app_version} · {settings.app_env}")

apply_theme(theme)

try:
    if uploaded is not None:
        raw = load_tabular_data(uploaded)
        source_name = uploaded.name
        source_kind = "Uploaded dataset"
        record_audit_event("dataset_uploaded", session_id, filename=uploaded.name, rows=len(raw))
    else:
        raw = load_sample_data()
        source_name = "PRISM synthetic enterprise dataset"
        source_kind = "Synthetic demo"
except (ValueError, OSError) as error:
    logger.exception("Unable to load data")
    record_audit_event("data_load_failed", session_id, error_type=type(error).__name__)
    st.error(f"Unable to load data: {error}")
    st.stop()

if raw.empty:
    st.error("The selected dataset contains no rows.")
    st.stop()

analysis = enrich_analysis_frame(raw)
profile = profile_dataset(analysis)
relationships = strongest_correlations(analysis)
anomalies = anomaly_summary(analysis)

st.title("PRISM")
st.subheader("Enterprise Reporting, Analytics & Data Strategy")
st.caption("Turn uploaded data into evidence, foresight, decisions and measurable strategy.")

if source_kind == "Synthetic demo":
    st.info(
        "Demonstration mode uses deterministic synthetic data only. It does not contain real "
        "company, customer, employee or transaction records."
    )

st.caption(f"Source: {source_name} · {profile.rows:,} rows analysed")
metric_columns = st.columns(6)
metric_columns[0].metric("Rows", f"{profile.rows:,}")
metric_columns[1].metric("Columns", f"{profile.columns:,}")
metric_columns[2].metric("Data quality", f"{profile.quality_score:.1f}%")
metric_columns[3].metric("Numeric", len(profile.numeric_columns))
metric_columns[4].metric("Date fields", len(profile.date_columns))
metric_columns[5].metric("Missing", f"{profile.missing_pct:.1f}%")

coverage_rows = [
    ("Descriptive reporting", True, "Available for every uploaded dataset"),
    ("Relationship discovery", len(profile.numeric_columns) >= 2, "Needs 2+ numeric fields"),
    (
        "Segmentation",
        bool(profile.categorical_columns and profile.numeric_columns),
        "Category + metric",
    ),
    ("Forecasting", bool(profile.date_columns and profile.numeric_columns), "Date + metric"),
    ("Prediction", profile.rows >= 40 and profile.columns >= 2, "40+ usable rows"),
    ("Strategy signals", True, "Generated from available evidence"),
]
coverage = pd.DataFrame(coverage_rows, columns=["Capability", "Ready", "Requirement"])
coverage["Status"] = coverage["Ready"].map({True: "Ready", False: "Needs more data"})

forecast_result = None
prediction_result: PredictionResult | None = st.session_state.get("prediction_result")
segment_result = None

tabs = st.tabs(
    [
        "Executive Overview",
        "Relationships",
        "Forecast",
        "Predict",
        "Strategy",
        "Data Quality",
    ]
)

with tabs[0]:
    left, right = st.columns([1.6, 1])
    with left:
        st.subheader("Analysis coverage")
        st.dataframe(
            coverage[["Capability", "Status", "Requirement"]],
            use_container_width=True,
            hide_index=True,
        )
    with right:
        st.subheader("Detected structure")
        st.write(f"Numeric measures: **{len(profile.numeric_columns)}**")
        st.write(f"Categories/text: **{len(profile.categorical_columns)}**")
        st.write(f"Dates: **{len(profile.date_columns)}**")
        st.write(f"Identifiers: **{len(profile.id_like_columns)}**")
        st.write(f"Potential outlier fields: **{len(anomalies)}**")

    if REQUIRED_COLUMNS.issubset(raw.columns):
        sales_result = validate_data(raw)
        if not sales_result.errors:
            sales = prepare_reporting_data(
                sales_result.dataframe.dropna(subset=["order_date", "quantity", "unit_price"])
            )
            kpis = calculate_kpis(sales)
            st.subheader("Recognised sales/order reporting layer")
            sales_columns = st.columns(5)
            sales_columns[0].metric("Revenue", f"€{kpis['revenue']:,.0f}")
            sales_columns[1].metric("Orders", f"{kpis['orders']:,}")
            sales_columns[2].metric("Units", f"{kpis['units']:,}")
            sales_columns[3].metric("Customers", f"{kpis['customers']:,}")
            sales_columns[4].metric("Average order", f"€{kpis['aov']:,.0f}")

    if profile.numeric_columns:
        selected_metric = st.selectbox(
            "Explore numeric metric",
            profile.numeric_columns,
            key="overview_metric",
        )
        numeric_series = pd.to_numeric(analysis[selected_metric], errors="coerce").dropna()
        if not numeric_series.empty:
            summary_columns = st.columns(4)
            summary_columns[0].metric("Mean", f"{numeric_series.mean():,.2f}")
            summary_columns[1].metric("Median", f"{numeric_series.median():,.2f}")
            summary_columns[2].metric("Minimum", f"{numeric_series.min():,.2f}")
            summary_columns[3].metric("Maximum", f"{numeric_series.max():,.2f}")
            st.plotly_chart(
                px.histogram(
                    analysis,
                    x=selected_metric,
                    title=f"Distribution of {selected_metric}",
                ),
                use_container_width=True,
            )

with tabs[1]:
    st.subheader("Useful relationships")
    st.caption(
        "Correlations show association, not causation. Validate important relationships with "
        "domain knowledge, experiments or causal methods before using them as policy."
    )
    if relationships.empty:
        st.info("No material numeric relationships were detected with the current data.")
    else:
        st.dataframe(relationships, use_container_width=True, hide_index=True)
        corr_matrix = analysis.select_dtypes(include="number").corr()
        if 2 <= len(corr_matrix.columns) <= 20:
            st.plotly_chart(
                px.imshow(corr_matrix, text_auto=".2f", title="Correlation map"),
                use_container_width=True,
            )

    segment_candidates = [
        column
        for column in profile.categorical_columns
        if 2 <= analysis[column].nunique(dropna=True) <= 30
    ]
    if segment_candidates and profile.numeric_columns:
        st.subheader("Segment performance")
        segment_column, metric_column, aggregation = st.columns(3)
        with segment_column:
            selected_segment = st.selectbox("Segment", segment_candidates, key="segment_column")
        with metric_column:
            selected_segment_metric = st.selectbox(
                "Metric",
                profile.numeric_columns,
                key="segment_metric",
            )
        with aggregation:
            selected_aggregation = st.selectbox(
                "Aggregation",
                ["sum", "mean", "median"],
                key="segment_aggregation",
            )
        segment_result = segment_performance(
            analysis,
            selected_segment,
            selected_segment_metric,
            selected_aggregation,
        )
        if not segment_result.empty:
            st.plotly_chart(
                px.bar(
                    segment_result,
                    x="value",
                    y=selected_segment,
                    orientation="h",
                    title=f"{selected_segment_metric} by {selected_segment}",
                ),
                use_container_width=True,
            )

with tabs[2]:
    st.subheader("Forecasting")
    if not profile.date_columns or not profile.numeric_columns:
        st.info("Forecasting requires at least one detected date field and one numeric measure.")
    else:
        forecast_controls = st.columns(4)
        with forecast_controls[0]:
            forecast_date = st.selectbox("Date", profile.date_columns, key="forecast_date")
        with forecast_controls[1]:
            forecast_metric = st.selectbox(
                "Measure", profile.numeric_columns, key="forecast_metric"
            )
        with forecast_controls[2]:
            forecast_aggregation = st.selectbox(
                "Aggregation",
                ["sum", "mean", "median"],
                key="forecast_aggregation",
            )
        with forecast_controls[3]:
            forecast_periods = st.slider("Months ahead", 3, 18, 6, key="forecast_periods")

        monthly = build_monthly_series(
            analysis,
            forecast_date,
            forecast_metric,
            forecast_aggregation,
        )
        try:
            forecast_result = forecast_monthly_series(monthly, forecast_periods)
            actual = forecast_result.history.rename(columns={"actual": "value"}).assign(
                series="Actual"
            )
            predicted = forecast_result.forecast.rename(columns={"forecast": "value"}).assign(
                series="Forecast"
            )
            chart_data = pd.concat(
                [actual[["date", "value", "series"]], predicted[["date", "value", "series"]]],
                ignore_index=True,
            )
            st.plotly_chart(
                px.line(chart_data, x="date", y="value", color="series", markers=True),
                use_container_width=True,
            )
            forecast_columns = st.columns(4)
            forecast_columns[0].metric("Direction", forecast_result.trend)
            forecast_columns[1].metric(
                "Projected change",
                f"{forecast_result.projected_change_pct:+.1f}%",
            )
            forecast_columns[2].metric(
                "Backtest MAE",
                "N/A"
                if forecast_result.backtest_mae is None
                else f"{forecast_result.backtest_mae:,.2f}",
            )
            forecast_columns[3].metric(
                "Backtest MAPE",
                "N/A"
                if forecast_result.backtest_mape is None
                else f"{forecast_result.backtest_mape:.1f}%",
            )
            st.caption(
                "Forecast uses a transparent trend + monthly seasonality model. The statistical "
                "range is available in the forecast table below and should be treated as "
                "uncertainty, not a guarantee."
            )
            with st.expander("Forecast table"):
                st.dataframe(forecast_result.forecast, use_container_width=True, hide_index=True)
        except ValueError as error:
            st.info(str(error))

with tabs[3]:
    st.subheader("Predictive analysis")
    st.caption(
        "Choose an outcome and PRISM will test whether the remaining usable fields can predict "
        "it on held-out data. Driver importance is predictive association, not proof of causality."
    )
    target_candidates = [
        column
        for column in analysis.columns
        if column not in profile.id_like_columns and analysis[column].nunique(dropna=True) > 1
    ]
    if not target_candidates:
        st.info("No suitable prediction target was detected.")
    else:
        target = st.selectbox("Outcome / target", target_candidates, key="prediction_target")
        default_features = [
            column
            for column in analysis.columns
            if column != target
            and column not in profile.id_like_columns
            and column not in profile.date_columns
            and analysis[column].nunique(dropna=True) <= max(60, int(profile.rows * 0.5))
        ][:12]
        features = st.multiselect(
            "Predictor fields",
            [column for column in analysis.columns if column != target],
            default=default_features,
            key="prediction_features",
        )
        if st.button("Run predictive model", type="primary"):
            try:
                prediction_result = train_predictive_model(analysis, target, features)
                st.session_state["prediction_result"] = prediction_result
                st.session_state["prediction_signature"] = (source_name, target, tuple(features))
                record_audit_event(
                    "predictive_model_run",
                    session_id,
                    target=target,
                    rows=prediction_result.training_rows + prediction_result.test_rows,
                )
            except ValueError as error:
                st.warning(str(error))
                prediction_result = None

        signature = st.session_state.get("prediction_signature")
        if prediction_result is not None and signature and signature[0] == source_name:
            result_columns = st.columns(4)
            result_columns[0].metric("Task", prediction_result.task)
            result_columns[1].metric(
                prediction_result.primary_metric,
                f"{prediction_result.primary_score:,.3f}",
            )
            result_columns[2].metric(
                prediction_result.secondary_metric,
                f"{prediction_result.secondary_score:,.3f}",
            )
            result_columns[3].metric(
                prediction_result.baseline_metric,
                f"{prediction_result.baseline_score:,.3f}",
            )
            if prediction_result.warnings:
                for warning in prediction_result.warnings:
                    st.warning(warning)
            st.subheader("Predictive drivers")
            st.plotly_chart(
                px.bar(
                    prediction_result.feature_importance.head(12),
                    x="importance",
                    y="feature",
                    orientation="h",
                ),
                use_container_width=True,
            )

with tabs[4]:
    st.subheader("Strategy Studio")
    st.caption(
        "PRISM translates the evidence available in this dataset into prioritised decision "
        "signals. These are hypotheses and planning prompts, not autonomous business decisions."
    )
    signals = build_strategy_signals(
        profile,
        relationships,
        anomalies,
        forecast_result,
        prediction_result,
        segment_result,
    )
    for signal in signals:
        with st.container(border=True):
            st.markdown(f"**{signal.priority} priority · {signal.theme}**")
            st.write(signal.evidence)
            st.write(f"**Recommended action:** {signal.recommendation}")
            st.caption(f"Decision impact: {signal.decision_impact}")

    strategy_table = pd.DataFrame(
        [
            {
                "priority": signal.priority,
                "theme": signal.theme,
                "evidence": signal.evidence,
                "recommendation": signal.recommendation,
                "decision_impact": signal.decision_impact,
            }
            for signal in signals
        ]
    )
    st.download_button(
        "Download strategy signals",
        strategy_table.to_csv(index=False).encode(),
        "prism_strategy_signals.csv",
        "text/csv",
    )

with tabs[5]:
    st.subheader("Data quality and structure")
    inventory = column_inventory(analysis, profile)
    st.dataframe(inventory, use_container_width=True, hide_index=True)

    quality_columns = st.columns(4)
    quality_columns[0].metric("Duplicate rows", f"{profile.duplicate_rows:,}")
    quality_columns[1].metric("Duplicate rate", f"{profile.duplicate_pct:.1f}%")
    quality_columns[2].metric("Constant fields", len(profile.constant_columns))
    quality_columns[3].metric("Potential IDs", len(profile.id_like_columns))

    st.subheader("Potential anomalies")
    if anomalies.empty:
        st.success("No numeric IQR-based anomaly concentrations were detected.")
    else:
        st.dataframe(anomalies, use_container_width=True, hide_index=True)

    with st.expander("Data preview"):
        st.dataframe(analysis.head(100), use_container_width=True, hide_index=True)

    st.download_button(
        "Download analysed data",
        analysis.to_csv(index=False).encode(),
        "prism_analysed_data.csv",
        "text/csv",
        on_click=lambda: record_audit_event("data_exported", session_id, rows=len(analysis)),
    )

st.divider()
st.caption(
    f"{settings.app_name} v{settings.app_version} · Enterprise Intelligence Foundation · "
    "Synthetic demo by default"
)
