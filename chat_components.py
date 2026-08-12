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


def suggested_questions_row(questions: list[str], key_prefix: str) -> str | None:
    """Render suggested-question chips; returns the clicked question, if any."""
    clicked = None
    cols = st.columns(len(questions))
    for i, q in enumerate(questions):
        with cols[i]:
            if st.button(q, key=f"{key_prefix}_{i}", use_container_width=True):
                clicked = q
    return clicked
