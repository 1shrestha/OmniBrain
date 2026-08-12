"""
pages/chat.py — main RAG chat interface with source citations.
"""

import streamlit as st

from components.cards import page_header, alert
from components.chat_components import render_sources, suggested_questions_row
from services import api_client

SUGGESTED_QUESTIONS = [
    "What does this website offer?",
    "Summarize the website.",
    "What are its main services?",
]


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


def render() -> None:
    project = st.session_state.get("current_project")
    subtitle = "Ask anything about your analyzed website or documents."
    if project:
        subtitle += f'  ·  Project: **{project["name"]}**'
    page_header("🧠 OmniBrain AI", subtitle)

    top_l, top_r = st.columns([5, 1.3])
    with top_r:
        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state["chat_history"][_project_key()] = []
            st.rerun()

    history = _history()

    if not history:
        st.caption("Try one of these to get started:")
        clicked = suggested_questions_row(SUGGESTED_QUESTIONS, key_prefix="suggest")
        if clicked:
            with st.spinner("Thinking..."):
                _ask(clicked)
            st.rerun()

    for msg in history:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("sources"):
                render_sources(msg["sources"])
            if msg["role"] == "assistant" and msg.get("time_ms") is not None:
                st.caption(f"⏱️ {msg['time_ms']} ms · model: {msg.get('model', 'unknown')}")

    prompt = st.chat_input("Ask OmniBrain about your website or documents...")
    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Retrieving context and generating an answer..."):
                _ask(prompt)
            last = history[-1]
            st.markdown(last["content"])
            if last.get("sources"):
                render_sources(last["sources"])
            if last.get("time_ms") is not None:
                st.caption(f"⏱️ {last['time_ms']} ms · model: {last.get('model', 'unknown')}")
