"""
app.py — OmniBrain Streamlit frontend entry point.

Run with:
    streamlit run app.py

This file only wires things together: page config, global CSS,
session state, sidebar navigation, and dispatch to the selected
page module. No business logic lives here — see services/api_client.py
for backend communication and pages/*.py for screen content.
"""

from pathlib import Path

import streamlit as st

from config import configure_page, init_session_state
from components.sidebar import render_sidebar
from pages import dashboard, analyze, documents, chat, simulation, analytics, settings

PAGES = {
    "dashboard": dashboard,
    "analyze": analyze,
    "documents": documents,
    "chat": chat,
    "simulation": simulation,
    "analytics": analytics,
    "settings": settings,
}


def load_css() -> None:
    css_path = Path(__file__).parent / "assets" / "styles.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def main() -> None:
    configure_page()
    init_session_state()
    load_css()

    current_page = render_sidebar()
    page_module = PAGES.get(current_page, dashboard)
    page_module.render()


if __name__ == "__main__":
    main()
