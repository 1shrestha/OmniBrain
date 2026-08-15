"""
components/architecture.py — renders the OmniBrain architecture diagram.
"""

import streamlit as st

_LAYERS = [
    ("👤", "User"),
    ("🖥️", "Streamlit UI"),
    ("⚙️", "FastAPI Backend"),
]

_BRANCH = [("🕸️", "Web Scraper"), ("📄", "Documents")]

_TAIL = [
    ("🧩", "Data Processing"),
    ("🗄️", "RAG / Vector DB"),
    ("🤖", "AI Agents"),
    ("🎮", "Simulation Engine"),
    ("🧠", "OmniBrain UI"),
]


def render_architecture_diagram() -> None:
    for icon, label in _LAYERS:
        st.markdown(f'<div class="ob-arch-node">{icon} &nbsp;{label}</div>', unsafe_allow_html=True)
        st.markdown('<div class="ob-arch-arrow">↓</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        icon, label = _BRANCH[0]
        st.markdown(f'<div class="ob-arch-node">{icon} &nbsp;{label}</div>', unsafe_allow_html=True)
    with col2:
        icon, label = _BRANCH[1]
        st.markdown(f'<div class="ob-arch-node">{icon} &nbsp;{label}</div>', unsafe_allow_html=True)

    st.markdown('<div class="ob-arch-arrow">↓</div>', unsafe_allow_html=True)

    for icon, label in _TAIL:
        st.markdown(f'<div class="ob-arch-node">{icon} &nbsp;{label}</div>', unsafe_allow_html=True)
        if label != _TAIL[-1][1]:
            st.markdown('<div class="ob-arch-arrow">↓</div>', unsafe_allow_html=True)
