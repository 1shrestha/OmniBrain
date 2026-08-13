"""
API route definitions for OmniBrain.

Document Q&A (original, now fixed — see inline notes):
    POST   /upload                          Upload and process a PDF document
    POST   /chat                            Ask a question about documents/websites
    GET    /documents                       List all processed documents
    DELETE /documents/{id}                  Delete a specific document
    GET    /health                          Health check and system stats

Website intelligence + projects (new, matches the Streamlit frontend):
    POST   /analyze                         Scrape + index a website, creates a project
    GET    /projects                        List all projects
    GET    /projects/{id}/status             Poll analysis progress
    GET    /projects/{id}/chat-history       Retrieve a project's chat history
    POST   /projects/{id}/simulation/start   Start a simulation session
    GET    /projects/{id}/simulation/state   Get current simulation UI components
    POST   /projects/{id}/simulation/stop    Stop a simulation session
    GET    /analytics                        Aggregate usage analytics
"""

from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile, HTTPException

from app.core.dependencies import (
    verify_api_key,
    get_document_service,
    get_chat_service,
    get_analytics_service,
    get_website_service,
    get_project_service,
    get_simulation_service,
)
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyticsResponse,
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    DeleteResponse,
    DocumentListResponse,
    DocumentInfo,
    ErrorResponse,
    HealthResponse,
    ProjectInfo,
    ProjectListResponse,
    ProjectStatusResponse,
    SimulationStartResponse,
    SimulationStateResponse,
    SimulationStopResponse,
    SourceCitation,
    UploadResponse,
)
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.services.analytics_service import AnalyticsService
from app.services.website_service import WebsiteService
from app.services.project_service import ProjectService
from app.services.simulation_service import SimulationService
from app.core.exceptions import OmniBrainError
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════
# POST /upload
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/upload",
    response_model=UploadResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Upload and process a PDF document",
    description="Upload a PDF file. The backend extracts text, chunks it, generates embeddings, and indexes it in ChromaDB.",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload (max 50MB)"),
    project_id: Optional[str] = Form(default=None, description="Optional project to attach this document to"),
    document_service: DocumentService = Depends(get_document_service),
    _auth: None = Depends(verify_api_key),
) -> UploadResponse:
    """
    Handle file upload and document processing.

    Reads the uploaded PDF, processes it through the full pipeline
    (extraction → chunking → embedding → indexing), and returns
    the document ID and processing statistics.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    logger.info(f"Upload request: filename='{file.filename}', content_type='{file.content_type}'")

    try:
        file_bytes = await file.read()
        result = await document_service.upload_and_process(
            filename=file.filename,
            file_bytes=file_bytes,
            project_id=project_id,
        )
        return UploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            pages=result["pages"],
            chunks=result["chunks"],
            status=result["status"],
            message=result["message"],
            project_id=result.get("project_id"),
        )
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.exception("Unexpected error during upload")
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")


# ═══════════════════════════════════════════════════════════════════
# POST /chat
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}},
    summary="Ask a question about the documents or an analyzed website",
    description="Submit a question. The system retrieves relevant chunks (from documents and/or an analyzed website) and generates an answer using Gemini via the LangGraph workflow.",
)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    _auth: None = Depends(verify_api_key),
) -> ChatResponse:
    """
    Process a user question and return a context-aware answer with citations.

    The RAG pipeline:
    1. Embed the question
    2. Search ChromaDB for relevant chunks (optionally scoped to a project)
    3. Build context with source citations
    4. Run LangGraph workflow → Gemini generates the answer
    """
    logger.info(
        f"Chat request: question='{request.question[:100]}...' "
        f"(top_k={request.top_k}, project_id={request.project_id})"
    )

    try:
        result = await chat_service.ask(
            question=request.question,
            document_ids=request.document_ids,
            top_k=request.top_k,
            temperature=request.temperature,
            project_id=request.project_id,
        )

        sources = [
            SourceCitation(
                document_id=s["document_id"],
                filename=s["filename"],
                page_number=s["page_number"],
                chunk_index=s["chunk_index"],
                similarity_score=s["similarity_score"],
                snippet=s["snippet"],
                source_type=s.get("source_type", "document"),
                url=s.get("url"),
            )
            for s in result.get("sources", [])
        ]

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            processing_time_ms=result["processing_time_ms"],
            model_used=result["model_used"],
        )
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.exception("Unexpected error during chat")
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")


# ═══════════════════════════════════════════════════════════════════
# GET /documents
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/documents",
    response_model=DocumentListResponse,
    summary="List all processed documents",
    description="Returns metadata for all PDFs that have been uploaded and indexed.",
)
async def list_documents(
    document_service: DocumentService = Depends(get_document_service),
    _auth: None = Depends(verify_api_key),
) -> DocumentListResponse:
    """Return a list of all processed documents with their metadata."""
    try:
        documents = await document_service.get_all_documents()
        doc_infos = [
            DocumentInfo(
                document_id=doc["document_id"],
                filename=doc["filename"],
                pages=doc["pages"],
                chunks=doc["chunks"],
                file_size_bytes=doc["file_size_bytes"],
                created_at=doc["created_at"],
                status=doc["status"],
                project_id=doc.get("project_id"),
            )
            for doc in documents
        ]
        return DocumentListResponse(documents=doc_infos, total=len(doc_infos))
    except Exception as exc:
        logger.exception("Error listing documents")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {exc}")


# ═══════════════════════════════════════════════════════════════════
# DELETE /documents/{id}
# ═══════════════════════════════════════════════════════════════════

@router.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Delete a processed document",
    description="Removes a document from the vector store, file system, and analytics registry.",
)
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service),
    _auth: None = Depends(verify_api_key),
) -> DeleteResponse:
    """Delete a document and all its associated data."""
    try:
        result = await document_service.delete_document(document_id)
        return DeleteResponse(
            document_id=result["document_id"],
            status=result["status"],
            message=result["message"],
        )
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.exception(f"Error deleting document {document_id}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {exc}")


# ═══════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns system health, version, uptime, and indexing statistics.",
)
async def health_check(
    document_service: DocumentService = Depends(get_document_service),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> HealthResponse:
    """
    Return system health information.

    Uses the injected singleton AnalyticsService (see core/dependencies.py)
    rather than constructing a throwaway one — the original code built a
    fresh AnalyticsService() here, so uptime always read ~0 seconds.
    """
    stats = document_service.get_health_stats()

    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime_seconds=analytics_service.get_uptime_seconds(),
        documents_indexed=stats["documents_indexed"],
        total_chunks=stats["total_chunks"],
    )


# ═══════════════════════════════════════════════════════════════════
# POST /analyze
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Analyze a website",
    description="Crawls a website (same-domain, breadth-first, up to max_pages), extracts and indexes its content, and creates a project for it.",
)
async def analyze_website(
    request: AnalyzeRequest,
    website_service: WebsiteService = Depends(get_website_service),
    _auth: None = Depends(verify_api_key),
) -> AnalyzeResponse:
    """Scrape and index a website, matching the Analyze Website page's pipeline."""
    logger.info(f"Analyze request: url='{request.url}' max_pages={request.max_pages}")
    try:
        result = website_service.analyze(request.url, max_pages=request.max_pages)
        return AnalyzeResponse(**result)
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except Exception as exc:
        logger.exception("Unexpected error during website analysis")
        raise HTTPException(status_code=500, detail=f"Internal server error: {exc}")


# ═══════════════════════════════════════════════════════════════════
# GET /projects
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="List all projects",
    description="Returns every project created via /analyze (and any documents attached to them).",
)
async def list_projects(
    project_service: ProjectService = Depends(get_project_service),
    _auth: None = Depends(verify_api_key),
) -> ProjectListResponse:
    projects = project_service.get_all_projects()
    infos = [ProjectInfo(**p) for p in projects]
    return ProjectListResponse(projects=infos, total=len(infos))


# ═══════════════════════════════════════════════════════════════════
# GET /projects/{id}/status
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/projects/{project_id}/status",
    response_model=ProjectStatusResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Get a project's analysis status",
)
async def get_project_status(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    _auth: None = Depends(verify_api_key),
) -> ProjectStatusResponse:
    try:
        project = project_service.require_project(project_id)
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    progress = 100 if project["status"] == "completed" else 50
    return ProjectStatusResponse(project_id=project_id, status=project["status"], progress=progress)


# ═══════════════════════════════════════════════════════════════════
# GET /projects/{id}/chat-history
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/projects/{project_id}/chat-history",
    response_model=ChatHistoryResponse,
    summary="Get a project's chat history",
    description="Chat history is recorded automatically whenever /chat is called with a matching project_id.",
)
async def get_chat_history(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
    _auth: None = Depends(verify_api_key),
) -> ChatHistoryResponse:
    messages = project_service.get_chat_history(project_id)
    return ChatHistoryResponse(
        project_id=project_id,
        messages=[ChatHistoryMessage(**m) for m in messages],
    )


# ═══════════════════════════════════════════════════════════════════
# POST /projects/{id}/simulation/start
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/simulation/start",
    response_model=SimulationStartResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Start a simulation session for a project",
)
async def start_simulation(
    project_id: str,
    agent: str = Body(default="General Assistant", embed=True),
    simulation_service: SimulationService = Depends(get_simulation_service),
    _auth: None = Depends(verify_api_key),
) -> SimulationStartResponse:
    try:
        result = simulation_service.start(project_id, agent=agent)
        return SimulationStartResponse(**result)
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ═══════════════════════════════════════════════════════════════════
# GET /projects/{id}/simulation/state
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/projects/{project_id}/simulation/state",
    response_model=SimulationStateResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    summary="Get the current simulation's dynamic UI components",
)
async def get_simulation_state(
    project_id: str,
    simulation_service: SimulationService = Depends(get_simulation_service),
    _auth: None = Depends(verify_api_key),
) -> SimulationStateResponse:
    try:
        result = simulation_service.get_state(project_id)
        return SimulationStateResponse(**result)
    except OmniBrainError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ═══════════════════════════════════════════════════════════════════
# POST /projects/{id}/simulation/stop
# ═══════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/simulation/stop",
    response_model=SimulationStopResponse,
    summary="Stop a project's simulation session",
)
async def stop_simulation(
    project_id: str,
    simulation_service: SimulationService = Depends(get_simulation_service),
    _auth: None = Depends(verify_api_key),
) -> SimulationStopResponse:
    result = simulation_service.stop(project_id)
    return SimulationStopResponse(**result)


# ═══════════════════════════════════════════════════════════════════
# GET /analytics
# ═══════════════════════════════════════════════════════════════════

@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    summary="Aggregate usage analytics",
    description="Combines document stats, project/website stats, and chat query stats into one dashboard payload.",
)
async def get_analytics(
    document_service: DocumentService = Depends(get_document_service),
    project_service: ProjectService = Depends(get_project_service),
    _auth: None = Depends(verify_api_key),
) -> AnalyticsResponse:
    doc_stats = document_service.get_health_stats()
    projects = project_service.get_all_projects()
    websites_analyzed = sum(1 for p in projects if p.get("url"))

    return AnalyticsResponse(
        websites_analyzed=websites_analyzed,
        documents_processed=doc_stats["documents_indexed"],
        ai_queries=project_service.query_count,
        total_chunks=doc_stats["total_chunks"],
        avg_response_time_ms=project_service.avg_response_time_ms,
        simulation_sessions=project_service.active_simulation_count(),
    )
