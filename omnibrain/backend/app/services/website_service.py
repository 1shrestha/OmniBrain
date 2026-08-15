"""
services/website_service.py

Orchestrates the website half of the pipeline described in the
frontend spec: Website -> Pages -> Content -> Chunks -> Embeddings ->
Vector Database, mirroring what DocumentService already does for
PDFs. Reuses PDFService.clean_text/chunk_document rather than
duplicating chunking logic — a website page and a PDF page are both
just "text with a page number" by the time they reach that step.
"""

import time
from typing import Any, Optional

from app.core.config import settings
from app.core.exceptions import ProcessingError
from app.core.logger import get_logger
from app.database.embeddings import EmbeddingGenerator
from app.database.vector_store import VectorStore
from app.services.pdf_service import PDFService
from app.services.project_service import ProjectService
from app.services.scraper_service import ScraperService, normalize_url

logger = get_logger(__name__)

# Common page slugs mapped to friendly section labels, used to turn
# "/about-us" into "About" etc. for the "Extracted Website Content" UI.
_SECTION_LABEL_HINTS = [
    ("about", "About"),
    ("service", "Services"),
    ("product", "Products"),
    ("contact", "Contact"),
    ("pricing", "Pricing"),
    ("blog", "Blog"),
    ("faq", "FAQ"),
    ("team", "Team"),
    ("career", "Careers"),
]


def _label_for_page(url: str, index: int, title: str) -> str:
    if index == 0:
        return "Home"
    path = url.lower()
    for hint, label in _SECTION_LABEL_HINTS:
        if hint in path:
            return label
    return title[:40] if title else f"Page {index + 1}"


class WebsiteService:
    def __init__(
        self,
        scraper_service: Optional[ScraperService] = None,
        pdf_service: Optional[PDFService] = None,
        embedding_generator: Optional[EmbeddingGenerator] = None,
        vector_store: Optional[VectorStore] = None,
        project_service: Optional[ProjectService] = None,
    ) -> None:
        self._scraper = scraper_service or ScraperService()
        self._pdf_service = pdf_service or PDFService()
        self._embedding_generator = embedding_generator or EmbeddingGenerator()
        self._vector_store = vector_store or VectorStore()
        self._project_service = project_service or ProjectService()

    def analyze(self, url: str, max_pages: Optional[int] = None) -> dict[str, Any]:
        """
        Crawl a website, index its content, and return everything the
        Analyze Website page needs to render — including a fresh project.

        Raises:
            InvalidURLError, WebsiteFetchError, ProcessingError
        """
        start_time = time.time()
        max_pages = max_pages or settings.SCRAPER_MAX_PAGES

        normalized_url = normalize_url(url)
        pages = self._scraper.crawl(normalized_url, max_pages=max_pages)

        if not pages:
            raise ProcessingError(f"No content could be extracted from {normalized_url}")

        website_title = pages[0]["title"]

        project = self._project_service.create_project(name=website_title, url=normalized_url)
        project_id = project["project_id"]

        # ── Preprocess + chunk each page (reusing the PDF pipeline) ──────
        preprocessed_pages = []
        sections: dict[str, str] = {}
        total_links: set[str] = set()
        total_forms = 0

        for i, page in enumerate(pages):
            cleaned = self._pdf_service.clean_text(page["text"])
            preprocessed_pages.append({
                "page_number": i + 1,
                "raw_text": page["text"],
                "cleaned_text": cleaned,
                "char_count": len(cleaned),
            })
            label = _label_for_page(page["url"], i, page["title"])
            if label not in sections:
                preview = cleaned[:600] + ("..." if len(cleaned) > 600 else "")
                sections[label] = preview or "(No readable text content found on this page.)"
            total_links |= page["links"]
            total_forms += page["forms_count"]

        chunks = self._pdf_service.chunk_document(preprocessed_pages)
        if not chunks:
            raise ProcessingError(f"No text chunks could be created from {normalized_url}")

        chunk_texts = [c["text"] for c in chunks]
        embeddings = self._embedding_generator.generate(chunk_texts)

        chunk_ids: list[str] = []
        metadatas: list[dict[str, Any]] = []
        for i, chunk in enumerate(chunks):
            page_url = pages[0]["url"]
            # Best-effort: attribute the chunk to the first page it overlaps.
            if chunk["page_numbers"]:
                idx = chunk["page_numbers"][0] - 1
                if 0 <= idx < len(pages):
                    page_url = pages[idx]["url"]

            cid = f"web_{project_id}_chunk_{i:06d}"
            chunk_ids.append(cid)
            metadatas.append({
                "document_id": f"web_{project_id}",
                "filename": website_title,
                "chunk_index": i,
                "page_numbers": chunk["page_numbers"],
                "char_count": chunk["char_count"],
                "source_type": "website",
                "project_id": project_id,
                "url": page_url,
            })

        self._vector_store.add_chunks(chunk_ids, embeddings, chunk_texts, metadatas)

        elapsed = round(time.time() - start_time, 2)

        self._project_service.update_project(
            project_id,
            status="completed",
            pages=len(pages),
        )

        logger.info(
            f"Website analyzed | project={project_id} | pages={len(pages)} "
            f"| chunks={len(chunks)} | time={elapsed}s"
        )

        return {
            "project_id": project_id,
            "website_title": website_title,
            "url": normalized_url,
            "total_pages": len(pages),
            "content_sections": len(sections),
            "links_found": len(total_links),
            "forms_found": total_forms,
            "processing_time_seconds": elapsed,
            "sections": sections,
            "status": "completed",
        }
