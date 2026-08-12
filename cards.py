"""
components/cards.py — reusable card widgets used across pages.
"""

import streamlit as st


def badge(text: str, kind: str = "info") -> str:
    """Return an HTML badge span. kind: success | pending | error | info."""
    return f'<span class="ob-badge ob-badge-{kind}">{text}</span>'


def stat_card(icon: str, label: str, value, delta: str | None = None) -> None:
    delta_html = f'<div style="color:#1E9E5A;font-size:0.8rem;margin-top:0.25rem;">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="ob-stat-card">
            <div class="ob-stat-icon">{icon}</div>
            <div class="ob-stat-label">{label}</div>
            <div class="ob-stat-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def project_card(project: dict) -> None:
    status = project.get("status", "pending")
    status_kind = {"completed": "success", "processing": "pending", "failed": "error"}.get(status, "info")
    st.markdown(
        f"""
        <div class="ob-project-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div class="ob-project-name">{project.get('name', 'Untitled project')}</div>
                    <div class="ob-project-url">{project.get('url', '')}</div>
                </div>
                {badge(status.capitalize(), status_kind)}
            </div>
            <div class="ob-project-meta">
                📅 {project.get('date', '—')} &nbsp;•&nbsp;
                📄 {project.get('pages', 0)} pages &nbsp;•&nbsp;
                📁 {project.get('documents', 0)} documents
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert(message: str, kind: str = "info") -> None:
    icons = {"warning": "⚠️", "error": "⚠️", "info": "ℹ️"}
    st.markdown(
        f'<div class="ob-alert ob-alert-{kind}">{icons.get(kind, "ℹ️")} {message}</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="ob-page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ob-page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def section_title(title: str) -> None:
    st.markdown(f'<div class="ob-section-title">{title}</div>', unsafe_allow_html=True)
