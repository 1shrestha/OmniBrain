"""
Pydantic models for API request/response validation.

NOTE: this package is named `models` (lowercase). The original project
had it as `MODELS/`, which only imports correctly on case-insensitive
filesystems (Windows). On Linux — where this will actually deploy —
`from app.models.schemas import ...` would raise ModuleNotFoundError.
This lowercase package is the fix; `app/api/routes.py` has been
updated to import from here.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Upload ─────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response returned after a successful PDF upload and processing."""

    document_id: str = Field(..., description="Unique identifier for the uploaded document")
    filename: str = Field(..., description="Original filename")
    pages: int = Field(..., description="Number of pages processed")
    chunks: int = Field(..., description="Number of text chunks created")
    status: str = Field(default="success", description="Processing status")
    message: str = Field(default="Document processed successfully", description="Human-readable message")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp")
    project_id: Optional[str] = Field(default=None, description="Project this document was attached to, if any")


class ErrorResponse(BaseModel):
    """Standard error response payload."""

    detail: str = Field(..., description="Error description")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="ISO timestamp")


# ── Chat / Q&A ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for the chat / Q&A endpoint."""

    question: str = Field(..., min_length=1, max_length=4096, description="User's question")
    document_ids: Optional[list[str]] = Field(
        default=None,
        description="Optional list of document IDs to restrict search scope",
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Optional project ID — scopes retrieval to that project's documents and analyzed website",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of relevant chunks to retrieve")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Override model temperature")


class SourceCitation(BaseModel):
    """Citation for a source chunk used in the answer."""

    document_id: str = Field(..., description="Source document ID")
    filename: str = Field(..., description="Source filename")
    page_number: int = Field(..., description="Page number the chunk came from")
    chunk_index: int = Field(..., description="Chunk index within the document")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Retrieval similarity score")
    snippet: str = Field(..., max_length=500, description="Short text excerpt")
    source_type: str = Field(default="document", description="'document' or 'website'")
    url: Optional[str] = Field(default=None, description="Source page URL, for website-sourced chunks")


class ChatResponse(BaseModel):
    """Response returned after processing a user's question."""

    answer: str = Field(..., description="AI-generated answer")
    sources: list[SourceCitation] = Field(default_factory=list, description="Source citations")
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")
    model_used: str = Field(..., description="AI model that generated the answer")


class ChatHistoryMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: str


class ChatHistoryResponse(BaseModel):
    project_id: str
    messages: list[ChatHistoryMessage] = Field(default_factory=list)


# ── Document Management ────────────────────────────────────────────

class DocumentInfo(BaseModel):
    """Metadata about a processed document."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    pages: int = Field(..., description="Number of pages")
    chunks: int = Field(..., description="Number of chunks")
    file_size_bytes: int = Field(..., description="File size in bytes")
    created_at: str = Field(..., description="Upload timestamp (ISO)")
    status: str = Field(..., description="Processing status")
    project_id: Optional[str] = Field(default=None, description="Associated project, if any")


class DocumentListResponse(BaseModel):
    """Response listing all processed documents."""

    documents: list[DocumentInfo] = Field(default_factory=list, description="List of documents")
    total: int = Field(..., description="Total number of documents")


class DeleteResponse(BaseModel):
    """Response after deleting a document."""

    document_id: str = Field(..., description="ID of the deleted document")
    status: str = Field(default="deleted", description="Deletion status")
    message: str = Field(..., description="Human-readable message")


# ── Website Analysis ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    """Request body for POST /analyze."""

    url: str = Field(..., min_length=3, description="Website URL to analyze")
    max_pages: int = Field(default=15, ge=1, le=50, description="Crawl limit — how many same-domain pages to visit")


class AnalyzeResponse(BaseModel):
    """Response returned after a website has been scraped and indexed."""

    project_id: str = Field(..., description="Project created for this analysis")
    website_title: str
    url: str
    total_pages: int
    content_sections: int
    links_found: int
    forms_found: int
    processing_time_seconds: float
    sections: dict[str, str] = Field(default_factory=dict, description="Section label -> extracted text preview")
    status: str = Field(default="completed")


# ── Projects ───────────────────────────────────────────────────────

class ProjectInfo(BaseModel):
    project_id: str
    name: str
    url: Optional[str] = None
    status: str
    created_at: str
    pages: int = 0
    documents: int = 0


class ProjectListResponse(BaseModel):
    projects: list[ProjectInfo] = Field(default_factory=list)
    total: int


class ProjectStatusResponse(BaseModel):
    project_id: str
    status: str
    progress: int = Field(..., ge=0, le=100)


# ── Simulation ─────────────────────────────────────────────────────

class SimulationComponent(BaseModel):
    """A single backend-driven UI instruction the frontend renders dynamically."""

    type: str = Field(..., description="text | buttons | cards | search | recommendations | table | form | status")
    content: Optional[str] = None
    items: Optional[list[Any]] = None
    placeholder: Optional[str] = None
    fields: Optional[list[str]] = None
    rows: Optional[list[Any]] = None
    message: Optional[str] = None
    level: Optional[str] = None


class SimulationStartResponse(BaseModel):
    session_id: str
    project_id: str
    status: str


class SimulationStateResponse(BaseModel):
    project_id: str
    status: str
    components: list[dict[str, Any]] = Field(default_factory=list)


class SimulationStopResponse(BaseModel):
    project_id: str
    status: str


# ── Analytics ──────────────────────────────────────────────────────

class AnalyticsResponse(BaseModel):
    websites_analyzed: int = 0
    documents_processed: int = 0
    ai_queries: int = 0
    total_chunks: int = 0
    avg_response_time_ms: float = 0.0
    simulation_sessions: int = 0


# ── Health ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="ok", description="Service status")
    version: str = Field(..., description="Application version")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    documents_indexed: int = Field(..., description="Number of documents in the vector store")
    total_chunks: int = Field(..., description="Total chunks indexed")
