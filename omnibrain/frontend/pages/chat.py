"""
pages/chat.py — main RAG chat interface with source citations.
"""

import streamlit as st

from components.cards import alert, page_hero
from components.chat_components import (
    chat_meta_chip,
    render_sources,
    suggested_questions_row,
    typing_indicator,
)
from services import api_client

SUGGESTED_QUESTIONS = [
    "What does this website offer?",
    "Summarize the website.",
    "What are its main services?",
]
SUGGESTED_ICONS = ["🌐", "📝", "🛠️"]


def _project_key() -> str:
    project = st.session_state.get("current_project")
    return project["name"] if project else "__default__"


def _history() -> list:
    key = _project_key()
    return st.session_state["chat_history"].setdefault(key, [])


def _ask(question: str) -> None:
    history = _history()
    history.append({"role": "user", "content": question})

    project = st.session_state.get("current_project")
    project_id = project.get("project_id") if project else None
    result = api_client.send_chat_message(question, project_id=project_id)

    if result["ok"]:
        data = result["data"]
        history.append({
            "role": "assistant",
            "content": data.get("answer", ""),
            "sources": data.get("sources", []),
            "model": data.get("model_used"),
            "time_ms": data.get("processing_time_ms"),
        })
        st.session_state["stats"]["ai_conversations"] += 1
    else:
        history.append({
            "role": "assistant",
            "content": f"⚠️ {result['error']}",
            "sources": [],
            "error": True,
        })


def _render_hero() -> None:
    project = st.session_state.get("current_project")
    badge = f"📁 Project: {project['name']}" if project else "🌍 No project selected — using default index"
    page_hero(
        "🧠",
        "OmniBrain AI",
        "Ask anything about your analyzed website or documents — answers come with cited sources.",
        badge_text=badge,
    )


def _render_message(msg: dict) -> None:
    with st.chat_message("user" if msg["role"] == "user" else "assistant"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("error"):
            alert("The backend couldn't answer that — see the message above for details.", kind="error")
        if msg["role"] == "assistant" and msg.get("sources"):
            render_sources(msg["sources"])
        if msg["role"] == "assistant" and msg.get("time_ms") is not None:
            chat_meta_chip(msg.get("model"), msg.get("time_ms"))


def render() -> None:
    _render_hero()

    top_l, top_r = st.columns([5, 1.3])
    with top_r:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state["chat_history"][_project_key()] = []
            st.rerun()

    history = _history()

    if not history:
        st.caption("✨ Try one of these to get started:")
        clicked = suggested_questions_row(
            SUGGESTED_QUESTIONS, key_prefix="suggest", icons=SUGGESTED_ICONS
        )
        if clicked:
            with st.chat_message("assistant"):
                placeholder = st.empty()
                with placeholder:
                    typing_indicator()
                _ask(clicked)
                placeholder.empty()
            st.rerun()

    for msg in history:
        _render_message(msg)

    prompt = st.chat_input("Ask OmniBrain about your website or documents...")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            placeholder = st.empty()
            with placeholder:
                typing_indicator("Retrieving context and generating an answer")
            _ask(prompt)
            placeholder.empty()

            last = history[-1]
            st.markdown(last["content"])
            if last.get("error"):
                alert("The backend couldn't answer that — see the message above for details.", kind="error")
            if last.get("sources"):
                render_sources(last["sources"])
            if last.get("time_ms") is not None:
                chat_meta_chip(last.get("model"), last.get("time_ms"))
