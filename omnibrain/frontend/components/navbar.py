"""
components/navbar.py — slim top bar showing breadcrumb + quick refresh.
Used optionally at the top of a page, above the page header.
"""

import streamlit as st

from config import NAV_ITEMS


def render_navbar() -> None:
    current = st.session_state.get("current_page", "dashboard")
    label = next((item["label"] for item in NAV_ITEMS if item["key"] == current), "Dashboard")
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(
            f'<div style="color:#6B7189;font-size:0.85rem;">🧠 OmniBrain &nbsp;/&nbsp; <b style="color:#1B1F3B;">{label}</b></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div style="text-align:right;color:#6B7189;font-size:0.8rem;">'
            f'{st.session_state.get("theme_mode", "Light")} mode</div>',
            unsafe_allow_html=True,
        )
