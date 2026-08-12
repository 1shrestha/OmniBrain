"""
pages/analyze.py — enter a URL, watch the scrape/index pipeline, inspect results.
"""

from datetime import datetime
from urllib.parse import urlparse

import streamlit as st

from components.cards import page_header, section_title, stat_card, alert
from components.progress import run_pipeline_animation
from services import api_client

PIPELINE_STEPS = [
    "URL Validated",
    "Website Connected",
    "Scraping Website",
    "Processing Content",
    "Creating Knowledge Base",
    "Initializing AI Agent",
]


def _valid_url(url: str) -> bool:
    if not url:
        return False
    candidate = url if "://" in url else f"https://{url}"
    parsed = urlparse(candidate)
    return bool(parsed.netloc) and "." in parsed.netloc


def render() -> None:
    page_header("Website Analysis", "Point OmniBrain at a website and it will scrape, index, and understand it.")

    with st.form("analyze_form", clear_on_submit=False):
        url = st.text_input("Enter Website URL", placeholder="https://example.com")
        submitted = st.form_submit_button("🌐 Analyze Website", type="primary", use_container_width=False)

    if submitted:
        if not _valid_url(url):
            alert("Please enter a valid website URL.", "warning")
        else:
            progress_area = st.empty()
            with st.spinner("Talking to the backend..."):
                run_pipeline_animation(progress_area, PIPELINE_STEPS, delay=0.35)
                result = api_client.analyze_website(url)

            if result["ok"] or result.get("demo"):
                data = result["data"]
                st.session_state["analysis_result"] = data
                st.session_state["analysis_status"][url] = "completed"

                project_name = data.get("website_title", url)
                new_project = {
                    "project_id": data.get("project_id"),
                    "name": project_name,
                    "url": url,
                    "status": "completed",
                    "date": datetime.now().strftime("%b %d, %Y"),
                    "pages": data.get("total_pages", 0),
                    "documents": 0,
                }
                st.session_state["projects"].insert(0, new_project)
                st.session_state["current_project"] = new_project
                st.session_state["stats"]["websites_analyzed"] += 1

                if result.get("demo"):
                    alert(
                        "The `/analyze` endpoint isn't available on the connected backend yet — "
                        "showing a demo result so you can preview the full experience.",
                        "info",
                    )
                st.success("Website analysis complete.")
            else:
                alert(f"Website analysis failed. {result['error']}", "error")

    result_data = st.session_state.get("analysis_result")
    if result_data:
        st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)
        section_title("Website Overview")

        c1, c2, c3 = st.columns(3)
        with c1:
            stat_card("📝", "Website Title", result_data.get("website_title", "—"))
        with c2:
            stat_card("📄", "Total Pages", result_data.get("total_pages", 0))
        with c3:
            stat_card("🧩", "Content Sections", result_data.get("content_sections", 0))

        c4, c5, c6 = st.columns(3)
        with c4:
            stat_card("🔗", "Links Found", result_data.get("links_found", 0))
        with c5:
            stat_card("📋", "Forms Found", result_data.get("forms_found", 0))
        with c6:
            stat_card("⏱️", "Processing Time", f'{result_data.get("processing_time_seconds", 0)}s')

        st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)
        section_title("Extracted Website Content")

        sections = result_data.get("sections", {})
        if not sections:
            st.caption("No section-level content was returned by the backend.")
        for name, content in sections.items():
            with st.expander(f"▾ {name}"):
                st.write(content)

        col_a, col_b = st.columns([1, 5])
        with col_a:
            if st.button("💬 Chat about this site", type="primary"):
                st.session_state["current_page"] = "chat"
                st.rerun()
