"""
pages/simulation.py — controls on the left, backend-driven dynamic
experience rendered on the right.

The backend can return a list of "components" describing what to draw
(text, buttons, cards, forms, tables, search boxes, recommendations,
status messages). `_render_component` is the single place that maps
a component type to Streamlit widgets — extend it as the backend
grows new component types.
"""

import streamlit as st

from components.cards import page_header, alert, badge
from services import api_client


def _render_component(component: dict) -> None:
    ctype = component.get("type")

    if ctype == "text":
        st.markdown(component.get("content", ""))

    elif ctype == "buttons":
        items = component.get("items", [])
        cols = st.columns(len(items)) if items else []
        for col, item in zip(cols, items):
            with col:
                st.button(item, key=f"sim_btn_{item}", use_container_width=True)

    elif ctype == "search":
        st.text_input(component.get("placeholder", "Search..."), key="sim_search")

    elif ctype == "cards":
        items = component.get("items", [])
        cols = st.columns(min(len(items), 3) or 1)
        for i, item in enumerate(items):
            with cols[i % len(cols)]:
                st.markdown(
                    f"""<div class="ob-card">
                        <b>{item.get('title', '')}</b>
                        <div style="color:#6B7189;font-size:0.85rem;">{item.get('description', '')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    elif ctype == "recommendations":
        st.markdown("**Recommended for you**")
        items = component.get("items", [])
        cols = st.columns(min(len(items), 3) or 1)
        for i, item in enumerate(items):
            with cols[i % len(cols)]:
                st.markdown(
                    f"""<div class="ob-card">
                        <b>{item.get('title', '')}</b>
                        <div style="color:#6B7189;font-size:0.85rem;">{item.get('description', '')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    elif ctype == "table":
        st.dataframe(component.get("rows", []), use_container_width=True)

    elif ctype == "form":
        with st.form(key=f"sim_form_{id(component)}"):
            for field in component.get("fields", []):
                st.text_input(field)
            st.form_submit_button("Submit")

    elif ctype == "status":
        alert(component.get("message", ""), component.get("level", "info"))

    else:
        st.caption(f"Unrecognized component type from backend: `{ctype}`")


def render() -> None:
    page_header("🤖 OmniBrain Simulation", "Interact with an AI-generated representation of the analyzed website.")

    projects = st.session_state.get("projects", [])
    project_names = [p["name"] for p in projects] or ["No projects yet"]
    name_to_id = {p["name"]: p.get("project_id") for p in projects}

    left, right = st.columns([1, 2.4])

    with left:
        st.markdown('<div class="ob-card">', unsafe_allow_html=True)
        st.markdown("**Simulation Controls**")

        selected_project_name = st.selectbox("Select project", project_names, disabled=not projects)
        selected_project_id = name_to_id.get(selected_project_name)
        agent = st.selectbox("Select AI agent", ["General Assistant", "Sales Agent", "Support Agent"])

        running = st.session_state.get("simulation_running", False)

        col_start, col_stop = st.columns(2)
        with col_start:
            if st.button(
                "▶️ Start", type="primary", use_container_width=True,
                disabled=running or not projects or not selected_project_id,
            ):
                result = api_client.start_simulation(selected_project_id, agent)
                if result["ok"]:
                    st.session_state["simulation_running"] = True
                    st.session_state["stats"]["active_simulations"] += 1
                    state = api_client.get_simulation_state(selected_project_id)
                    st.session_state["simulation_state"] = state["data"] if state["ok"] else {}
                    st.rerun()
                else:
                    alert(result["error"], "error")
        with col_stop:
            if st.button("⏹️ Stop", use_container_width=True, disabled=not running):
                api_client.stop_simulation(selected_project_id)
                st.session_state["simulation_running"] = False
                st.session_state["stats"]["active_simulations"] = max(
                    0, st.session_state["stats"]["active_simulations"] - 1
                )
                st.rerun()

        if st.button("🔄 Reset simulation", use_container_width=True):
            st.session_state["simulation_state"] = {}
            st.session_state["simulation_running"] = False
            st.rerun()

        st.markdown(
            badge("Running" if running else "Stopped", "success" if running else "pending"),
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        state = st.session_state.get("simulation_state")
        if not st.session_state.get("simulation_running") or not state:
            st.markdown(
                """
                <div class="ob-card" style="text-align:center;padding:3rem 1rem;">
                    <div style="font-size:2rem;">🤖</div>
                    <div style="font-weight:600;margin-top:0.4rem;">No simulation running</div>
                    <div style="color:#6B7189;font-size:0.88rem;">
                        Select a project and press Start to generate an interactive experience.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            if state.get("demo"):
                alert(
                    "Live simulation endpoints aren't available on the connected backend yet — "
                    "this is a demo experience showing how backend-driven components render.",
                    "info",
                )
            st.markdown('<div class="ob-card">', unsafe_allow_html=True)
            for component in state.get("components", []):
                _render_component(component)
                st.markdown("<div style='margin:0.5rem 0;'></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
