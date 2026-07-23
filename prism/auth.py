"""Lightweight access gate that can later be replaced by an identity provider."""

from __future__ import annotations

import hmac

import streamlit as st

from prism.config import settings
from prism.observability import record_audit_event


def require_access(session_id: str) -> None:
    """Stop page execution until the optional application passcode is accepted."""
    if not settings.enable_authentication:
        return
    if st.session_state.get("authenticated", False):
        return

    st.title(settings.app_name)
    st.caption("Secure product intelligence workspace")
    with st.form("prism_login"):
        access_code = st.text_input("Access code", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        configured = settings.app_access_code.get_secret_value()
        if configured and hmac.compare_digest(access_code, configured):
            st.session_state.authenticated = True
            record_audit_event("login_success", session_id)
            st.rerun()
        else:
            record_audit_event("login_failed", session_id)
            st.error("The access code is not valid.")
    st.info("Authentication is optional in the public demo and can be enabled through deployment secrets.")
    st.stop()
