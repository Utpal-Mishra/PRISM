import platform
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from prism.auth import require_access
from prism.config import settings
from prism.observability import configure_logging, read_audit_log, record_audit_event

st.set_page_config(page_title="PRISM Settings", page_icon="⚙", layout="wide")
configure_logging()
session_id = st.session_state.setdefault("session_id", str(uuid.uuid4()))
require_access(session_id)

st.title("Settings")
st.caption("Runtime preferences and deployment readiness")

st.subheader("Appearance")
theme = st.segmented_control(
    "Theme",
    ["System", "Light", "Dark"],
    default=st.session_state.get("theme", "System"),
)
st.session_state.theme = theme
st.info(
    "This browser preference is session-based. The deployment default remains in "
    "`.streamlit/config.toml`."
)

st.subheader("Application mode")
st.toggle("Demo mode", value=settings.enable_demo_mode, disabled=True)
st.toggle("Authentication", value=settings.enable_authentication, disabled=True)

st.subheader("Runtime")
left, right = st.columns(2)
left.metric("PRISM version", settings.app_version)
left.write(f"Environment: `{settings.app_env}`")
right.write(f"Python: `{platform.python_version()}`")
right.write(f"Platform: `{platform.system()}`")

st.subheader("Activity audit")
st.caption(
    "Audit storage is local and ephemeral on Streamlit Community Cloud until a database "
    "is introduced."
)
audit = read_audit_log()
st.download_button(
    "Download audit log",
    audit,
    "prism_audit.jsonl",
    "application/x-ndjson",
    disabled=not bool(audit),
)

if st.button("Record settings review"):
    record_audit_event("settings_reviewed", session_id, theme=theme)
    st.success("Audit event recorded.")
