"""Session-level theme controls for the Streamlit interface."""

import streamlit as st

THEMES = ("Dark", "Light", "System")


def apply_theme(theme: str) -> None:
    """Apply PRISM's minimal enterprise visual system."""
    if theme == "System":
        return

    if theme == "Dark":
        background = "#0B1020"
        secondary = "#121A2C"
        elevated = "#172033"
        text = "#F3F6FC"
        muted = "#A8B3C7"
        border = "#27344C"
        accent = "#8AB4FF"
    else:
        background = "#F7F9FC"
        secondary = "#FFFFFF"
        elevated = "#F1F4F9"
        text = "#172033"
        muted = "#5F6B7D"
        border = "#DCE3EE"
        accent = "#315EA8"

    st.markdown(
        f"""
        <style>
        .stApp {{ background: {background}; color: {text}; }}
        [data-testid="stSidebar"] {{ background: {secondary}; }}
        [data-testid="stMetric"], [data-testid="stExpander"],
        [data-testid="stDataFrame"], [data-testid="stFileUploader"] {{
            background: {secondary};
            border: 1px solid {border};
            border-radius: 0.85rem;
        }}
        [data-testid="stMetric"] {{ padding: 0.8rem; }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: {secondary};
            border-color: {border};
        }}
        .stTabs [data-baseweb="tab-list"] {{ gap: 0.35rem; }}
        .stTabs [data-baseweb="tab"] {{
            background: {elevated};
            border-radius: 0.65rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }}
        .stTabs [aria-selected="true"] {{ color: {accent}; }}
        .stButton button, .stDownloadButton button {{
            border-radius: 0.7rem;
            border: 1px solid {border};
        }}
        h1, h2, h3, p, label, .stMarkdown {{ color: {text}; }}
        [data-testid="stCaptionContainer"] {{ color: {muted}; }}
        a {{ color: {accent}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def theme_selector(key: str = "theme") -> str:
    """Render a session-level theme selector and return its value."""
    current = st.session_state.get(key, "Dark")
    theme = st.selectbox("Appearance", THEMES, index=THEMES.index(current), key=f"{key}_selector")
    st.session_state[key] = theme
    return theme
