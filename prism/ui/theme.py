"""Session-level theme controls for the Streamlit interface."""

import streamlit as st

THEMES = ("System", "Light", "Dark")


def apply_theme(theme: str) -> None:
    """Apply a minimal CSS theme for the current Streamlit session."""
    if theme == "System":
        return

    if theme == "Dark":
        background = "#111827"
        secondary = "#1F2937"
        text = "#F3F4F6"
        border = "#374151"
    else:
        background = "#FFFFFF"
        secondary = "#F5F7F6"
        text = "#1F2937"
        border = "#E5E7EB"

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {background}; color: {text}; }}
        [data-testid="stSidebar"] {{ background-color: {secondary}; }}
        [data-testid="stMetric"], [data-testid="stExpander"] {{
            background-color: {secondary};
            border: 1px solid {border};
            border-radius: 0.75rem;
            padding: 0.75rem;
        }}
        h1, h2, h3, p, label, .stMarkdown, [data-testid="stCaptionContainer"] {{ color: {text}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def theme_selector(key: str = "theme") -> str:
    """Render a session-level theme selector and return its value."""
    current = st.session_state.get(key, "System")
    theme = st.selectbox("Appearance", THEMES, index=THEMES.index(current), key=f"{key}_selector")
    st.session_state[key] = theme
    return theme
