"""
components/sidebar.py — persistent left navigation, connection status,
current project, and user chip.
"""

import streamlit as st

from config import NAV_ITEMS
from services import api_client


def _refresh_backend_status() -> None:
    result = api_client.health_check()
    st.session_state["backend_connected"] = bool(result["ok"])
    st.session_state["ai_status"] = bool(result["ok"])


def render_sidebar() -> str:
    """Draws the sidebar and returns the currently selected page key."""
    with st.sidebar:
        st.markdown('<div class="ob-logo">🧠 OmniBrain</div>', unsafe_allow_html=True)
        st.markdown('<hr class="ob-nav-divider">', unsafe_allow_html=True)

        for item in NAV_ITEMS:
            is_active = st.session_state["current_page"] == item["key"]
            wrapper_class = "ob-nav-active" if is_active else ""
            st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
            if st.button(
                f'{item["icon"]}  {item["label"]}',
                key=f"nav_{item['key']}",
                use_container_width=True,
            ):
                st.session_state["current_page"] = item["key"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<hr class="ob-nav-divider">', unsafe_allow_html=True)

        if st.session_state.get("backend_connected") is None:
            _refresh_backend_status()

        connected = st.session_state.get("backend_connected")
        ai_active = st.session_state.get("ai_status")

        backend_dot = "ob-dot-green" if connected else "ob-dot-red"
        backend_label = "Backend Connected" if connected else "Backend Offline"
        ai_dot = "ob-dot-green" if ai_active else "ob-dot-gray"
        ai_label = "AI Engine Active" if ai_active else "AI Engine Idle"

        st.markdown(
            f"""
            <div class="ob-status-row"><span class="ob-dot {backend_dot}"></span>{backend_label}</div>
            <div class="ob-status-row"><span class="ob-dot {ai_dot}"></span>{ai_label}</div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("🔄 Refresh status", key="refresh_status_btn", use_container_width=True):
            _refresh_backend_status()
            st.rerun()

        project = st.session_state.get("current_project")
        project_label = project["name"] if project else "No project selected"
        st.markdown(
            f'<div class="ob-status-row" style="margin-top:0.5rem;">📁 <b>{project_label}</b></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div class="ob-user-chip">
                <div class="ob-user-avatar">U</div>
                <div>
                    <div style="font-weight:600;font-size:0.88rem;">Guest User</div>
                    <div style="color:#6B7189;font-size:0.75rem;">Free workspace</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state["current_page"]
