"""
pages/dashboard.py — landing page: stats, recent projects, quick actions.
"""

import streamlit as st

from components.cards import stat_card, project_card, page_header, section_title


def _go(page_key: str) -> None:
    st.session_state["current_page"] = page_key
    st.rerun()


def render() -> None:
    page_header("Welcome to OmniBrain 👋", "Turn websites and documents into intelligent AI experiences.")

    top_l, top_r = st.columns([5, 1.4])
    with top_r:
        if st.button("➕ Create New Analysis", type="primary", use_container_width=True):
            _go("analyze")

    stats = st.session_state["stats"]
    section_title("Overview")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("🌐", "Websites Analyzed", stats["websites_analyzed"])
    with c2:
        stat_card("📄", "Documents Processed", stats["documents_processed"])
    with c3:
        stat_card("💬", "AI Conversations", stats["ai_conversations"])
    with c4:
        stat_card("🤖", "Active Simulations", stats["active_simulations"])

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)

    left, right = st.columns([2.1, 1])

    with left:
        section_title("Recent Projects")
        projects = st.session_state["projects"]
        if not projects:
            st.markdown(
                """
                <div class="ob-card" style="text-align:center;padding:2.4rem 1rem;">
                    <div style="font-size:2rem;">📭</div>
                    <div style="font-weight:600;margin-top:0.4rem;">No projects yet</div>
                    <div style="color:#6B7189;font-size:0.9rem;margin-top:0.2rem;">
                        Analyze a website or upload a document to get started.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for idx, project in enumerate(projects):
                project_card(project)
                if st.button("Open Project →", key=f"open_project_{idx}", use_container_width=True):
                    st.session_state["current_project"] = project
                    _go("chat")

    with right:
        section_title("Quick Actions")
        if st.button("🌐  Analyze Website", use_container_width=True):
            _go("analyze")
        if st.button("📄  Upload Document", use_container_width=True):
            _go("documents")
        if st.button("💬  Start AI Chat", use_container_width=True):
            _go("chat")
        if st.button("🤖  Open Simulation", use_container_width=True):
            _go("simulation")
