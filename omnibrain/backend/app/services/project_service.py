"""
services/project_service.py

In-memory project registry. A "project" is the unit the frontend
groups everything under: it may have an analyzed website, zero or
more uploaded documents, a chat history, and a simulation session.

Kept intentionally simple (a dict behind a lock-free singleton,
same pattern as AnalyticsService's document registry) — swap this
for a real database table without changing any route code, since
routes only ever talk to this service, never to storage directly.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.exceptions import ProjectNotFoundError
from app.core.logger import get_logger

logger = get_logger(__name__)


class ProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, dict[str, Any]] = {}
        self._chat_history: dict[str, list[dict[str, Any]]] = {}
        self._query_count = 0
        self._response_time_total_ms = 0
        self._simulation_sessions: dict[str, dict[str, Any]] = {}
        logger.info("ProjectService initialized")

    # ── Project lifecycle ────────────────────────────────────────────

    def create_project(self, name: str, url: Optional[str] = None) -> dict[str, Any]:
        project_id = str(uuid.uuid4())
        project = {
            "project_id": project_id,
            "name": name,
            "url": url,
            "status": "processing",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "pages": 0,
            "documents": 0,
        }
        self._projects[project_id] = project
        self._chat_history[project_id] = []
        logger.info(f"Project created: {project_id} ({name})")
        return project

    def get_project(self, project_id: str) -> Optional[dict[str, Any]]:
        return self._projects.get(project_id)

    def require_project(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        return project

    def get_all_projects(self) -> list[dict[str, Any]]:
        projects = list(self._projects.values())
        projects.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        return projects

    def update_project(self, project_id: str, **fields: Any) -> dict[str, Any]:
        project = self.require_project(project_id)
        project.update(fields)
        return project

    def increment_documents(self, project_id: str, by: int = 1) -> None:
        project = self._projects.get(project_id)
        if project:
            project["documents"] = project.get("documents", 0) + by

    # ── Chat history ──────────────────────────────────────────────────

    def append_chat_message(self, project_id: str, role: str, content: str) -> None:
        if project_id not in self._chat_history:
            self._chat_history[project_id] = []
        self._chat_history[project_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_chat_history(self, project_id: str) -> list[dict[str, Any]]:
        return self._chat_history.get(project_id, [])

    # ── Query analytics ────────────────────────────────────────────────

    def record_query(self, processing_time_ms: int) -> None:
        self._query_count += 1
        self._response_time_total_ms += processing_time_ms

    @property
    def query_count(self) -> int:
        return self._query_count

    @property
    def avg_response_time_ms(self) -> float:
        if self._query_count == 0:
            return 0.0
        return round(self._response_time_total_ms / self._query_count, 1)

    # ── Simulation sessions ─────────────────────────────────────────────

    def start_simulation(self, project_id: str, agent: str) -> dict[str, Any]:
        self.require_project(project_id)
        session_id = f"sim_{uuid.uuid4().hex[:10]}"
        session = {
            "session_id": session_id,
            "project_id": project_id,
            "agent": agent,
            "status": "running",
            "started_at": time.time(),
        }
        self._simulation_sessions[project_id] = session
        return session

    def stop_simulation(self, project_id: str) -> dict[str, Any]:
        session = self._simulation_sessions.get(project_id)
        if session:
            session["status"] = "stopped"
        return session or {"project_id": project_id, "status": "stopped"}

    def get_simulation_session(self, project_id: str) -> Optional[dict[str, Any]]:
        return self._simulation_sessions.get(project_id)

    def active_simulation_count(self) -> int:
        return sum(1 for s in self._simulation_sessions.values() if s.get("status") == "running")
