"""
OmniBrain — global frontend configuration.

Centralizes page config, default settings and constants so the rest
of the app never hardcodes strings that might change later.
"""

import streamlit as st

APP_NAME = "OmniBrain"
APP_ICON = "🧠"
APP_TAGLINE = "Turn websites and documents into intelligent AI experiences."

DEFAULT_BACKEND_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
REQUEST_TIMEOUT_SECS = 30
UPLOAD_TIMEOUT_SECS = 120

NAV_ITEMS = [
    {"key": "dashboard", "label": "Dashboard", "icon": "🏠"},
    {"key": "analyze", "label": "Analyze Website", "icon": "🌐"},
    {"key": "documents", "label": "Documents", "icon": "📄"},
    {"key": "chat", "label": "OmniBrain Chat", "icon": "💬"},
    {"key": "simulation", "label": "Simulation", "icon": "🤖"},
    {"key": "analytics", "label": "Analytics", "icon": "📊"},
    {"key": "settings", "label": "Settings", "icon": "⚙️"},
]

PRIMARY_PURPLE = "#6C5CE7"
PRIMARY_BLUE = "#4F7CFF"
ACCENT_PINK = "#FFC2D1"
ACCENT_GREEN = "#B8E6D5"
NAVY_TEXT = "#1B1F3B"
MUTED_TEXT = "#6B7189"
BG_LIGHT = "#F7F8FC"
CARD_BG = "#FFFFFF"
BORDER_COLOR = "#ECEBFA"


def configure_page() -> None:
    """Must be the first Streamlit call in the app."""
    st.set_page_config(
        page_title=f"{APP_NAME} — AI Website Intelligence",
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )


def init_session_state() -> None:
    """Populate st.session_state with every key the app relies on."""
    defaults = {
        "current_page": "dashboard",
        "backend_url": DEFAULT_BACKEND_URL,
        "api_key": "",
        "backend_connected": None,
        "ai_status": None,
        "theme_mode": "Light",
        "current_project": None,
        "projects": [],
        "documents": [],
        "chat_history": {},
        "analysis_status": {},
        "analysis_result": {},
        "simulation_state": {},
        "simulation_running": False,
        "stats": {
            "websites_analyzed": 0,
            "documents_processed": 0,
            "ai_conversations": 0,
            "active_simulations": 0,
        },
        "toast_queue": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
