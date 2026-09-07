import sys
import uuid
from pathlib import Path

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
    "PRISM converts uploaded business data into trusted reporting, analytical evidence, "
    "predictive signals, forecasts and practical strategy recommendations."
)

st.subheader("Current release")
st.write(
    f"Version **{settings.app_version}** introduces the enterprise intelligence foundation "
    "for domain-agnostic analysis and decision support."
)

st.subheader("Intelligence roadmap")
st.markdown(
    """
1. Reporting and KPI Engine
2. Relationship and Driver Intelligence
3. Forecasting and Predictive Analytics
4. Customer and Commercial Intelligence
5. Supply Chain and Operations Intelligence
6. Sustainability Intelligence
7. Scenario and Decision Simulation
8. Strategy Advisor and Governance
"""
)

st.subheader("Design principles")
st.markdown(
    "Trusted data · Minimal interface · Explainable outputs · Practical recommendations · "
    "Enterprise readiness"
)
