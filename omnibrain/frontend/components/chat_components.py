"""
components/chat_components.py — rendering helpers for the AI Chat page.
"""

import streamlit as st


def render_sources(sources: list[dict]) -> None:
    """Render a 'Sources' expander beneath an AI answer."""
    if not sources:
        return
    with st.expander(f"📚 Sources ({len(sources)})"):
        for src in sources:
            title = src.get("filename") or src.get("page_title") or src.get("title", "Source")
            meta_bits = []
            if src.get("page_number") is not None:
                meta_bits.append(f"page {src['page_number']}")
            if src.get("url"):
                meta_bits.append(src["url"])
            if src.get("similarity_score") is not None:
                meta_bits.append(f"match {round(src['similarity_score'] * 100)}%")
            meta = " · ".join(str(m) for m in meta_bits)
            snippet = src.get("snippet") or src.get("chunk") or ""
            st.markdown(
                f"""
                <div class="ob-card" style="margin-bottom:0.6rem;padding:0.8rem 1rem;">
                    <div class="ob-source-title">📄 {title}</div>
                    <div class="ob-source-meta">{meta}</div>
                    <div style="font-size:0.87rem;color:#3A3F5C;margin-top:0.35rem;">{snippet}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def suggested_questions_row(
    questions: list[str],
    key_prefix: str,
    icons: list[str] | None = None,
) -> str | None:
    """Render suggested-question chips as hover-lift cards; returns the clicked question, if any."""
    clicked = None
    icons = icons or ["💡"] * len(questions)
    cols = st.columns(len(questions))
    for i, q in enumerate(questions):
        with cols[i]:
            st.markdown(
                f'<div class="ob-suggest-card"><div class="ob-suggest-icon">{icons[i % len(icons)]}</div>',
                unsafe_allow_html=True,
            )
            if st.button(q, key=f"{key_prefix}_{i}", use_container_width=True):
                clicked = q
            st.markdown("</div>", unsafe_allow_html=True)
    return clicked


def typing_indicator(label: str = "OmniBrain is thinking") -> None:
    """Animated bouncing-dots 'typing...' indicator, shown while waiting on the backend."""
    st.markdown(
        f"""
        <div class="ob-typing">
            {label}
            <span class="ob-typing-dots"><span></span><span></span><span></span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chat_meta_chip(model: str | None, time_ms: int | None) -> None:
    """Small pill showing which model answered and how long it took."""
    bits = []
    if time_ms is not None:
        bits.append(f"⏱️ {time_ms} ms")
    if model:
        bits.append(f"🧠 {model}")
    if not bits:
        return
    st.markdown(
        f'<span class="ob-chat-meta-chip">{" · ".join(bits)}</span>',
        unsafe_allow_html=True,
    )
