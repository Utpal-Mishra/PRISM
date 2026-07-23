from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from prism.auth import require_access
from prism.config import settings
from prism.observability import configure_logging

st.set_page_config(page_title="About PRISM", page_icon="◈", layout="wide")
configure_logging()
session_id = st.session_state.setdefault("session_id", str(uuid.uuid4()))
require_access(session_id)

st.title("About PRISM")
st.caption("Product Reporting Intelligence & Strategy Management")
st.write(
    "PRISM converts product reporting data into trusted performance metrics, "
    "clear business observations, and progressively richer strategic decisions."
)

st.subheader("Current release")
st.write(f"Version **{settings.app_version}** adds the production-readiness foundation around the reporting engine.")

st.subheader("Eight-module roadmap")
st.markdown(
    """
1. Reporting and KPI Engine
2. Forecasting Engine
3. Customer Intelligence
4. Marketing Intelligence
5. Supply Chain Intelligence
6. Sustainability Intelligence
7. Scenario Simulator
8. Strategy Advisor
"""
)

st.subheader("Design principles")
st.markdown("Trusted data · Minimal interface · Explainable outputs · Practical recommendations · Deployment readiness")
