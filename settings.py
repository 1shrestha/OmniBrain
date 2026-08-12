"""
pages/settings.py — API configuration, appearance, project settings,
and the architecture overview.
"""

import streamlit as st

from components.cards import page_header, section_title, alert, badge
from components.architecture import render_architecture_diagram
from services import api_client


def render() -> None:
    page_header("Settings", "Configure how OmniBrain talks to your backend and manage this session.")

    section_title("API Configuration")
    with st.form("api_config_form"):
        backend_url = st.text_input("Backend URL", value=st.session_state["backend_url"])
        api_key = st.text_input(
            "API Key (optional, only sent as a header — never shown once saved)",
            type="password",
            value="",
            placeholder="Leave blank to keep current key" if st.session_state.get("api_key") else "",
        )
        saved = st.form_submit_button("💾 Save configuration", type="primary")

    if saved:
        st.session_state["backend_url"] = backend_url.strip() or st.session_state["backend_url"]
        if api_key:
            st.session_state["api_key"] = api_key
        result = api_client.health_check()
        st.session_state["backend_connected"] = result["ok"]
        st.session_state["ai_status"] = result["ok"]
        if result["ok"]:
            st.success("Connected to backend successfully.")
        else:
            alert(result["error"], "error")

    connected = st.session_state.get("backend_connected")
    st.markdown(
        f"**Status:** {badge('Connected', 'success') if connected else badge('Offline', 'error')}",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"**AI Model Status:** {badge('Active', 'success') if connected else badge('Unavailable', 'error')}",
        unsafe_allow_html=True,
    )

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)

    section_title("Appearance")
    st.session_state["theme_mode"] = st.radio(
        "Theme preference", ["Light", "Dark"], index=0 if st.session_state["theme_mode"] == "Light" else 1,
        horizontal=True,
    )
    if st.session_state["theme_mode"] == "Dark":
        st.caption("Dark mode is coming soon — OmniBrain currently ships with a light, minimal theme.")

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)

    section_title("Project Settings")
    project = st.session_state.get("current_project")
    st.write(f"**Current project:** {project['name'] if project else 'None selected'}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear project data", disabled=not project):
            st.session_state["current_project"] = None
            st.success("Project cleared.")
    with col2:
        if st.button("♻️ Reset session"):
            for key in ["chat_history", "documents", "projects", "analysis_result", "simulation_state"]:
                st.session_state[key] = {} if isinstance(st.session_state[key], dict) else []
            st.session_state["current_project"] = None
            st.session_state["simulation_running"] = False
            st.success("Session reset.")
            st.rerun()

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)

    section_title("How OmniBrain Works")
    render_architecture_diagram()
