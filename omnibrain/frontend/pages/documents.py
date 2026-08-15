"""
pages/documents.py — upload documents, watch the processing pipeline,
browse and delete previously indexed documents.
"""

import streamlit as st

from components.cards import page_hero, section_title, alert, badge
from components.progress import run_pipeline_animation
from services import api_client

PIPELINE_STEPS = ["Upload", "Extract", "Clean", "Chunk", "Embed", "Store"]
ALLOWED_TYPES = ["pdf", "txt", "docx"]


def _refresh_documents() -> None:
    result = api_client.list_documents()
    if result["ok"] and result["data"]:
        st.session_state["documents"] = result["data"].get("documents", [])


def render() -> None:
    page_hero("📄", "Document Upload", "Upload PDFs, text files, or Word documents to add them to the knowledge base.")

    st.markdown(
        """
        <div class="ob-card" style="text-align:center;padding:2.2rem 1rem;border:2px dashed #ECEBFA;">
            <div style="font-size:2.2rem;">📄</div>
            <div style="font-weight:700;margin-top:0.4rem;">Upload your documents</div>
            <div style="color:#6B7189;font-size:0.88rem;">Drop files below or browse — PDF, TXT, DOCX supported.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Drop files here or browse files",
        type=ALLOWED_TYPES,
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        if st.button("⬆️ Process Documents", type="primary"):
            project = st.session_state.get("current_project")
            project_id = project.get("project_id") if project else None
            for file in uploaded_files:
                st.markdown(f"**{file.name}** &nbsp;·&nbsp; {round(len(file.getvalue()) / 1024, 1)} KB")
                progress_area = st.empty()
                run_pipeline_animation(progress_area, PIPELINE_STEPS, delay=0.25)

                result = api_client.upload_document(file, project_id=project_id)
                if result["ok"]:
                    data = result["data"]
                    st.success(
                        f"Processed **{data.get('filename', file.name)}** — "
                        f"{data.get('pages', '—')} pages, {data.get('chunks', '—')} chunks."
                    )
                    st.session_state["stats"]["documents_processed"] += 1
                    if st.session_state.get("current_project"):
                        st.session_state["current_project"]["documents"] = (
                            st.session_state["current_project"].get("documents", 0) + 1
                        )
                else:
                    alert(f"Failed to process {file.name}. {result['error']}", "error")
            _refresh_documents()

    st.markdown('<hr class="ob-divider">', unsafe_allow_html=True)
    section_title("Processed Documents")

    if st.button("🔄 Refresh list"):
        _refresh_documents()

    if not st.session_state.get("documents"):
        _refresh_documents()

    documents = st.session_state.get("documents", [])
    if not documents:
        st.caption("No documents processed yet, or the backend isn't reachable.")
    else:
        for doc in documents:
            col1, col2, col3, col4, col5 = st.columns([3, 1.2, 1.2, 1.4, 1])
            with col1:
                st.markdown(f"**📄 {doc.get('filename', 'Unknown')}**")
            with col2:
                st.caption(f"{doc.get('pages', '—')} pages")
            with col3:
                st.caption(f"{doc.get('chunks', '—')} chunks")
            with col4:
                st.markdown(badge(doc.get("status", "indexed").capitalize(), "success"), unsafe_allow_html=True)
            with col5:
                if st.button("🗑️", key=f"del_{doc.get('document_id')}"):
                    del_result = api_client.delete_document(doc.get("document_id"))
                    if del_result["ok"]:
                        st.success("Document deleted.")
                        _refresh_documents()
                        st.rerun()
                    else:
                        alert(del_result["error"], "error")
