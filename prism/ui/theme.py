"""Session-level theme controls for the legacy Streamlit interface."""

import streamlit as st

THEMES = ("Dark", "Light", "System")


def apply_theme(theme: str) -> None:
    """Apply PRISM's PALM/NEXUS-aligned enterprise visual system."""
    if theme == "System":
        return

    if theme == "Dark":
        background = "#07110D"
        secondary = "#0B1712"
        elevated = "#0E1D17"
        text = "#EDF7F1"
        muted = "#8FA39A"
        border = "#1E3229"
        accent = "#78E6AA"
        accent_2 = "#52D98D"
        lime = "#C8F56B"
        button_text = "#07110D"
    else:
        background = "#F6FAF7"
        secondary = "#FFFFFF"
        elevated = "#EDF5F0"
        text = "#173026"
        muted = "#61766B"
        border = "#D4E3DA"
        accent = "#218454"
        accent_2 = "#31A668"
        lime = "#A6D84F"
        button_text = "#07110D"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background:
                radial-gradient(circle at 78% -8%, color-mix(in srgb, {accent_2} 7%, transparent), transparent 28rem),
                {background};
            color: {text};
        }}
        [data-testid="stSidebar"] {{
            background: linear-gradient(180deg, {secondary}, {background});
            border-right: 1px solid {border};
        }}
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
            border: 1px solid {accent};
            background: linear-gradient(120deg, {lime}, {accent});
            color: {button_text};
            font-weight: 700;
        }}
        .stButton button:hover, .stDownloadButton button:hover {{
            border-color: {accent_2};
            filter: brightness(1.04);
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
