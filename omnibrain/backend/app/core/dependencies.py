"""
FastAPI dependency injection container.
Provides clean, testable dependencies for route handlers.

FIX: the original getters here (`return DocumentService()`, etc.) were
labeled "singleton" in their docstrings but actually constructed a
brand-new instance — with a brand-new empty in-memory registry — on
every single request. That meant AnalyticsService's document registry
(and therefore the whole /documents list, /health stats, and project
registry) reset itself after every API call. `@lru_cache()` on each
getter makes them real singletons for the life of the process, which
is what the rest of the code already assumed.
"""

from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Header, HTTPException

from app.core.config import settings
from app.core.logger import get_logger
from app.services.document_service import DocumentService
from app.services.pdf_service import PDFService
from app.services.analytics_service import AnalyticsService
from app.services.chat_service import ChatService
from app.services.scraper_service import ScraperService
from app.services.website_service import WebsiteService
from app.services.project_service import ProjectService
from app.services.simulation_service import SimulationService
from app.database.vector_store import VectorStore
from app.database.embeddings import EmbeddingGenerator
from app.ai.gemini_service import GeminiService
from app.ai.langgraph_workflow import LangGraphWorkflow

logger = get_logger(__name__)


def verify_api_key(x_api_key: str = Header(default=None)) -> None:
    """Dependency: validate API key if authentication is enabled."""
    if settings.AUTH_ENABLED:
        if not x_api_key or x_api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")


@lru_cache()
def get_embedding_generator() -> EmbeddingGenerator:
    """Singleton EmbeddingGenerator — the model is expensive to load."""
    return EmbeddingGenerator()


@lru_cache()
def get_vector_store() -> VectorStore:
    """Singleton VectorStore — wraps a persistent ChromaDB client."""
    return VectorStore()


@lru_cache()
def get_pdf_service() -> PDFService:
    return PDFService()


@lru_cache()
def get_analytics_service() -> AnalyticsService:
    """Singleton — holds the in-memory document registry."""
    return AnalyticsService()


@lru_cache()
def get_gemini_service() -> GeminiService:
    return GeminiService()


@lru_cache()
def get_langgraph_workflow() -> LangGraphWorkflow:
    return LangGraphWorkflow()


@lru_cache()
def get_scraper_service() -> ScraperService:
    return ScraperService()


@lru_cache()
def get_project_service() -> ProjectService:
    """Singleton — holds the in-memory project registry."""
    return ProjectService()


@lru_cache()
def get_document_service() -> DocumentService:
    return DocumentService(
        pdf_service=get_pdf_service(),
        analytics_service=get_analytics_service(),
        embedding_generator=get_embedding_generator(),
        vector_store=get_vector_store(),
        project_service=get_project_service(),
    )


@lru_cache()
def get_chat_service() -> ChatService:
    return ChatService(
        embedding_generator=get_embedding_generator(),
        vector_store=get_vector_store(),
        langgraph_workflow=get_langgraph_workflow(),
        project_service=get_project_service(),
    )


@lru_cache()
def get_website_service() -> WebsiteService:
    return WebsiteService(
        scraper_service=get_scraper_service(),
        pdf_service=get_pdf_service(),
        embedding_generator=get_embedding_generator(),
        vector_store=get_vector_store(),
        project_service=get_project_service(),
    )


@lru_cache()
def get_simulation_service() -> SimulationService:
    return SimulationService(project_service=get_project_service())


async def get_services() -> AsyncGenerator[dict, None]:
    """
    Composite dependency that yields all services.
    Useful for routes that need multiple dependencies.
    """
    yield {
        "pdf_service": get_pdf_service(),
        "analytics_service": get_analytics_service(),
        "document_service": get_document_service(),
        "chat_service": get_chat_service(),
        "vector_store": get_vector_store(),
        "embedding_generator": get_embedding_generator(),
        "gemini_service": get_gemini_service(),
        "langgraph_workflow": get_langgraph_workflow(),
        "scraper_service": get_scraper_service(),
        "website_service": get_website_service(),
        "project_service": get_project_service(),
        "simulation_service": get_simulation_service(),
    }
