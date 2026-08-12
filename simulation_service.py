"""
services/simulation_service.py

Generates the backend-driven UI component list that the frontend's
Simulation page renders dynamically (text, buttons, cards, search,
recommendations, etc. — see AnalyzeResponse.sections for the source
material). Deterministic and template-based rather than another LLM
call: it's fast, free, and doesn't fail if GEMINI_API_KEY isn't set,
which matters for a feature whose whole point is a live demo.

To make this LLM-generated instead, swap the body of `build_state()`
for a Gemini call that returns the same component list shape — no
other file needs to change.
"""

from typing import Any, Optional

from app.core.exceptions import ProjectNotFoundError, SimulationError
from app.core.logger import get_logger
from app.services.project_service import ProjectService

logger = get_logger(__name__)


class SimulationService:
    def __init__(self, project_service: Optional[ProjectService] = None) -> None:
        self._project_service = project_service or ProjectService()

    def start(self, project_id: str, agent: str = "General Assistant") -> dict[str, Any]:
        project = self._project_service.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        session = self._project_service.start_simulation(project_id, agent)
        return {"session_id": session["session_id"], "project_id": project_id, "status": "running"}

    def stop(self, project_id: str) -> dict[str, Any]:
        result = self._project_service.stop_simulation(project_id)
        return {"project_id": project_id, "status": result.get("status", "stopped")}

    def get_state(self, project_id: str) -> dict[str, Any]:
        project = self._project_service.require_project(project_id)
        session = self._project_service.get_simulation_session(project_id)
        if not session or session.get("status") != "running":
            raise SimulationError(f"No active simulation session for project '{project_id}'")

        components = self._build_components(project)
        return {"project_id": project_id, "status": "running", "components": components}

    def _build_components(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        name = project.get("name", "this website")
        url = project.get("url")

        components: list[dict[str, Any]] = [
            {
                "type": "text",
                "content": f"👋 Welcome to the simulated experience of **{name}**"
                + (f" ({url})" if url else "") + ".",
            },
            {
                "type": "buttons",
                "items": ["Explore Services", "View Products", "Contact Us"],
            },
            {
                "type": "search",
                "placeholder": f"Search {name}...",
            },
            {
                "type": "recommendations",
                "items": [
                    {
                        "title": "Most Relevant Page",
                        "description": f"Based on {project.get('pages', 0)} pages indexed from this site.",
                    },
                    {
                        "title": "Ask OmniBrain",
                        "description": "Try the chat tab for specific questions about this content.",
                    },
                ],
            },
            {
                "type": "status",
                "level": "info",
                "message": f"Simulation generated from {project.get('pages', 0)} indexed pages.",
            },
        ]
        return components
