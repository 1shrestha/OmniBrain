"""
services/api_client.py

Single point of contact between the Streamlit frontend and the
FastAPI backend. Every network call in the app goes through here —
pages never call `requests` directly.

Design rules:
    * Every function returns a plain dict: {"ok": bool, "data": ..., "error": ...}
      so pages never need to catch exceptions themselves.
    * Endpoints that don't exist on the backend yet (website analysis,
      simulation) degrade gracefully into a clearly-labeled "demo mode"
      response instead of crashing the UI. Once the backend implements
      them, only this file needs to change — no page code changes.
    * No business logic lives here. Collect input -> call API -> return result.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import requests
import streamlit as st

from config import DEFAULT_BACKEND_URL, API_PREFIX, REQUEST_TIMEOUT_SECS, UPLOAD_TIMEOUT_SECS


# ─────────────────────────────────────────────────────────────────────────
# Internals
# ─────────────────────────────────────────────────────────────────────────

def _base_url() -> str:
    """
    Every real route in the backend is mounted under /api/v1
    (see backend/app/main.py: app.include_router(router, prefix="/api/v1")).
    Centralizing that here means pages never need to know about it.
    """
    return (st.session_state.get("backend_url") or DEFAULT_BACKEND_URL).rstrip("/") + API_PREFIX


def _headers() -> dict:
    headers = {}
    api_key = st.session_state.get("api_key")
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _ok(data: Any) -> dict:
    return {"ok": True, "data": data, "error": None}


def _fail(error: str, demo: bool = False, data: Any = None) -> dict:
    return {"ok": False, "error": error, "demo": demo, "data": data}


def _request(method: str, path: str, **kwargs) -> dict:
    url = f"{_base_url()}{path}"
    timeout = kwargs.pop("timeout", REQUEST_TIMEOUT_SECS)
    try:
        resp = requests.request(method, url, headers=_headers(), timeout=timeout, **kwargs)
        if resp.status_code == 404:
            return _fail("This endpoint isn't available on the connected backend yet.", demo=True)
        resp.raise_for_status()
        if resp.content:
            return _ok(resp.json())
        return _ok(None)
    except requests.exceptions.ConnectionError:
        return _fail(
            "Unable to connect to the backend. Please check that the FastAPI "
            "server is running and reachable at the configured Backend URL."
        )
    except requests.exceptions.Timeout:
        return _fail("The request timed out. The backend may be under heavy load.")
    except requests.exceptions.HTTPError:
        detail = None
        try:
            detail = resp.json().get("detail")
        except Exception:
            pass
        return _fail(detail or f"Backend returned an error ({resp.status_code}).")
    except Exception as exc:  # noqa: BLE001 - surfaced to the UI, never a raw traceback
        return _fail(f"Unexpected error while contacting the backend: {exc}")


# ─────────────────────────────────────────────────────────────────────────
# Health / status
# ─────────────────────────────────────────────────────────────────────────

def health_check() -> dict:
    """GET /health — used for the sidebar connection indicators."""
    return _request("GET", "/health")


# ─────────────────────────────────────────────────────────────────────────
# Website analysis
# (Not yet implemented on the backend — degrades to demo mode.)
# ─────────────────────────────────────────────────────────────────────────

def analyze_website(url: str) -> dict:
    """POST /analyze — kicks off scraping + RAG indexing for a URL."""
    result = _request("POST", "/analyze", json={"url": url}, timeout=UPLOAD_TIMEOUT_SECS)
    if not result["ok"] and result.get("demo"):
        return _demo_analyze_website(url)
    return result


def _demo_analyze_website(url: str) -> dict:
    """Local fallback so the Analyze page stays fully interactive without a backend."""
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"https://{url}")
    domain = parsed.netloc or parsed.path
    title = domain.replace("www.", "").split(".")[0].capitalize()
    demo_data = {
        "project_id": f"demo-{abs(hash(url)) % 100000}",
        "website_title": f"{title} — Official Site",
        "url": url,
        "total_pages": 18,
        "content_sections": 6,
        "links_found": 142,
        "forms_found": 3,
        "processing_time_seconds": 7.4,
        "sections": {
            "Home": "Landing content introducing the brand, hero messaging, and primary calls to action.",
            "About": "Company background, mission statement, leadership team, and history.",
            "Services": "A breakdown of the core services offered, each with a short description and pricing hints.",
            "Products": "Product catalog entries including names, categories, and summaries.",
            "Contact": "Contact form fields, business address, support email, and phone number.",
        },
    }
    return _fail("demo", demo=True, data=demo_data)


def get_project_status(project_id: str) -> dict:
    """GET /projects/{id}/status — polling endpoint for analysis progress."""
    result = _request("GET", f"/projects/{project_id}/status")
    if not result["ok"] and result.get("demo"):
        return _ok({"status": "completed", "progress": 100})
    return result


# ─────────────────────────────────────────────────────────────────────────
# Documents
# ─────────────────────────────────────────────────────────────────────────

def upload_document(file, project_id: Optional[str] = None) -> dict:
    """POST /upload — multipart PDF upload, matches the live backend contract."""
    files = {"file": (file.name, file.getvalue(), file.type or "application/pdf")}
    data = {"project_id": project_id} if project_id else None
    return _request("POST", "/upload", files=files, data=data, timeout=UPLOAD_TIMEOUT_SECS)


def list_documents() -> dict:
    """GET /documents"""
    return _request("GET", "/documents")


def delete_document(document_id: str) -> dict:
    """DELETE /documents/{id}"""
    return _request("DELETE", f"/documents/{document_id}")


# ─────────────────────────────────────────────────────────────────────────
# Chat / RAG
# ─────────────────────────────────────────────────────────────────────────

def send_chat_message(
    question: str,
    document_ids: Optional[list] = None,
    top_k: int = 5,
    temperature: Optional[float] = None,
    project_id: Optional[str] = None,
) -> dict:
    """POST /chat — matches the live backend's ChatRequest schema exactly."""
    payload = {"question": question, "top_k": top_k}
    if document_ids:
        payload["document_ids"] = document_ids
    if temperature is not None:
        payload["temperature"] = temperature
    if project_id:
        payload["project_id"] = project_id
    return _request("POST", "/chat", json=payload)


def get_chat_history(project_id: str) -> dict:
    """GET /projects/{id}/chat-history — history is otherwise kept client-side."""
    result = _request("GET", f"/projects/{project_id}/chat-history")
    if not result["ok"] and result.get("demo"):
        return _ok({"messages": []})
    return result


# ─────────────────────────────────────────────────────────────────────────
# Simulation
# (Not yet implemented on the backend — degrades to a local demo agent.)
# ─────────────────────────────────────────────────────────────────────────

def start_simulation(project_id: str, agent: str = "default") -> dict:
    result = _request("POST", f"/projects/{project_id}/simulation/start", json={"agent": agent})
    if not result["ok"] and result.get("demo"):
        return _ok({"session_id": f"demo-{int(time.time())}", "status": "running", "demo": True})
    return result


def get_simulation_state(project_id: str) -> dict:
    result = _request("GET", f"/projects/{project_id}/simulation/state")
    if not result["ok"] and result.get("demo"):
        return _ok(_demo_simulation_state())
    return result


def _demo_simulation_state() -> dict:
    return {
        "demo": True,
        "components": [
            {"type": "text", "content": "Welcome to the simulated experience of your analyzed site."},
            {"type": "buttons", "items": ["Service A", "Service B", "Service C"]},
            {"type": "search", "placeholder": "Search the site..."},
            {
                "type": "recommendations",
                "items": [
                    {"title": "Featured Service", "description": "Most visited page from the crawl."},
                    {"title": "Popular Product", "description": "Highest-linked product page."},
                ],
            },
        ],
    }


def stop_simulation(project_id: str) -> dict:
    result = _request("POST", f"/projects/{project_id}/simulation/stop")
    if not result["ok"] and result.get("demo"):
        return _ok({"status": "stopped", "demo": True})
    return result


# ─────────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────────

def get_analytics(project_id: Optional[str] = None) -> dict:
    """GET /analytics — falls back to deriving stats from /health + /documents."""
    path = f"/projects/{project_id}/analytics" if project_id else "/analytics"
    result = _request("GET", path)
    if result["ok"]:
        return result
    if result.get("demo"):
        return _derive_analytics_from_health()
    return result


def _derive_analytics_from_health() -> dict:
    health = health_check()
    docs = list_documents()
    documents_indexed = 0
    total_chunks = 0
    if health["ok"]:
        documents_indexed = health["data"].get("documents_indexed", 0)
        total_chunks = health["data"].get("total_chunks", 0)
    doc_count = documents_indexed
    if docs["ok"]:
        doc_count = docs["data"].get("total", documents_indexed)
    return _ok({
        "demo": True,
        "documents_processed": doc_count,
        "total_chunks": total_chunks,
        "websites_analyzed": st.session_state.get("stats", {}).get("websites_analyzed", 0),
        "ai_queries": st.session_state.get("stats", {}).get("ai_conversations", 0),
    })
