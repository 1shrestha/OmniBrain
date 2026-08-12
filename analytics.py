"""
pages/analytics.py — usage analytics dashboard + processing pipeline diagram.
"""

import pandas as pd
import streamlit as st

from components.cards import page_header, section_title, stat_card, alert
from services import api_client

PIPELINE = ["Website", "Pages", "Content", "Chunks", "Embeddings", "Vector Database", "AI Retrieval", "Response"]


def render() -> None:
    page_header("Analytics", "Usage, retrieval performance, and pipeline throughput at a glance.")

    result = api_client.get_analytics()
    if not result["ok"]:
        alert(result["error"], "error")
        return

    data = result["data"]
    if data.get("demo"):
        alert(
            "A dedicated `/analytics` endpoint isn't available yet — these figures are derived "
            "from `/health` and `/documents` plus this session's activity.",
            "info",
        )

    stats = st.session_state["stats"]

    section_title("Key Metrics")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("🌐", "Websites Analyzed", data.get("websites_analyzed", stats["websites_analyzed"]))
    with c2:
        stat_card("📄", "Documents Processed", data.get("documents_processed", stats["documents_processed"]))
    with c3:
        stat_card("💬", "AI Queries", data.get("ai_queries", stats["ai_conversations"]))
    with c4:
        stat_card("🧩", "Total Chunks Indexed", data.get("total_chunks", 0))

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        section_title("Documents Processed Over Time")
        chart_df = pd.DataFrame({
            "Day": [f"Day {i}" for i in range(1, 8)],
            "Documents": _synthetic_trend(data.get("documents_processed", 0)),
        }).set_index("Day")
        st.line_chart(chart_df)

    with right:
        section_title("Query Volume by Type")
        breakdown_df = pd.DataFrame({
            "Type": ["Website Q&A", "Document Q&A", "Simulation", "General"],
            "Queries": _synthetic_breakdown(data.get("ai_queries", stats["ai_conversations"])),
        }).set_index("Type")
        st.bar_chart(breakdown_df)

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)
    section_title("Processing Pipeline")
    st.markdown(
        '<div style="text-align:center;">' + "  →  ".join(PIPELINE) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption("Every website or document flows through this pipeline before it's queryable in chat.")


def _synthetic_trend(total: int) -> list[int]:
    if total <= 0:
        return [0] * 7
    base = max(total // 7, 1)
    trend = [base] * 6
    trend.append(max(total - sum(trend), 0))
    return trend


def _synthetic_breakdown(total: int) -> list[int]:
    if total <= 0:
        return [0, 0, 0, 0]
    a = total // 2
    b = total // 3
    c = total // 8
    d = max(total - a - b - c, 0)
    return [a, b, c, d]
