"""
OmniBrain - Chunking Engine

Module: Layout Chunker

Purpose:
    Orchestrate chunking of a whole `LayoutDocument`: iterate its
    sections, delegate each one to `SemanticBuilder`, collect the
    resulting chunks, validate them, and return a `ChunkCollection`.

    This module contains no semantic chunking rules of its own —
    where a chunk boundary falls, how headings and captions are
    handled, how tables are kept intact, is entirely `SemanticBuilder`'s
    responsibility. This module only sequences the work.

    Pipeline:
        Receive LayoutDocument
          -> Iterate LayoutSections
          -> Call SemanticBuilder
          -> Collect Chunks
          -> Validate
          -> Return ChunkCollection
"""

from __future__ import annotations

import logging
import uuid

from src.models.chunk_models import ChunkCollection
from ..models.layout_models import LayoutDocument, LayoutSection
from .base_chunker import BaseChunker
from .chunk_validator import ChunkValidator
from .semantic_builder import SemanticBuilder

logger = logging.getLogger(__name__)


class ChunkingError(Exception):
    """Raised when chunk validation fails unrecoverably."""


class LayoutChunker(BaseChunker):
    """Orchestrates chunking of a `LayoutDocument` section by section.

    A single failed section is logged and skipped rather than aborting
    the whole document, since sections are chunked independently of
    one another; a failure in validation, which operates over the
    whole collection, is treated as fatal.
    """

    def __init__(
        self,
        semantic_builder: SemanticBuilder | None = None,
        validator: ChunkValidator | None = None,
    ) -> None:
        """Initializes the chunker with its collaborators.

        Args:
            semantic_builder: Builds chunks for a single section.
                Defaults to a new `SemanticBuilder`.
            validator: Validates and cleans the finished
                `ChunkCollection`. Defaults to a new `ChunkValidator`.
        """
        self._semantic_builder = semantic_builder or SemanticBuilder()
        self._validator = validator or ChunkValidator()

    def chunk_document(self, layout_document: LayoutDocument) -> ChunkCollection:
        """Chunks an entire document, section by section.

        Args:
            layout_document: A fully processed `LayoutDocument`.

        Returns:
            A validated `ChunkCollection` for the document.

        Raises:
            ChunkingError: If validation of the assembled chunks fails.
        """
        document_id = self._resolve_document_id(layout_document)
        source_path = layout_document.metadata.get("source_path", "")

        logger.info(
            "Chunking document '%s' (%d section(s))",
            layout_document.document_name,
            len(layout_document.sections),
        )

        chunks = self._build_chunks(
            layout_document, document_id, source_path
        )
        self._assign_global_chunk_index(chunks)

        collection = ChunkCollection(
            document_id=document_id,
            document_name=layout_document.document_name,
            source_path=source_path,
            chunks=chunks,
        )

        try:
            collection = self._validator.validate(collection)
        except Exception as exc:
            logger.exception(
                "Chunk validation failed for document '%s'",
                layout_document.document_name,
            )
            raise ChunkingError(
                f"Validation failed for '{layout_document.document_name}': {exc}"
            ) from exc

        logger.info(
            "Chunking complete for '%s': %d chunk(s)",
            layout_document.document_name,
            collection.chunk_count,
        )

        return collection

    def _build_chunks(
        self,
        layout_document: LayoutDocument,
        document_id: str,
        source_path: str,
    ) -> list[Chunk]:
        """Builds chunks for every section in the document.

        Args:
            layout_document: The document being chunked.
            document_id: Resolved document id, for traceability.
            source_path: Path to the source PDF.

        Returns:
            All chunks across all sections, in section order. A
            section that raises during chunking is logged and skipped
            rather than aborting the rest of the document.
        """
        chunks: list[Chunk] = []

        for section in layout_document.sections:
            section_chunks = self._build_section_chunks_safely(
                layout_document, document_id, source_path, section
            )
            chunks.extend(section_chunks)

        return chunks

    def _build_section_chunks_safely(
        self,
        layout_document: LayoutDocument,
        document_id: str,
        source_path: str,
        section: LayoutSection,
    ) -> list[Chunk]:
        """Builds chunks for one section, isolating failures to that section.

        Args:
            layout_document: The document being chunked.
            document_id: Resolved document id.
            source_path: Path to the source PDF.
            section: The section to chunk.

        Returns:
            Chunks for this section, or an empty list if chunking this
            section raised an exception.
        """
        try:
            return self._semantic_builder.build_section_chunks(
                document_id=document_id,
                document_name=layout_document.document_name,
                source_path=source_path,
                section=section,
                relationships=layout_document.relationships,
            )
        except Exception:
            logger.exception(
                "Failed to build chunks for section '%s' (%s); skipping",
                section.id,
                section.title or "untitled",
            )
            return []

    def _assign_global_chunk_index(self, chunks: list[Chunk]) -> None:
        """Renumbers chunks with a document-wide index, in place.

        `SemanticBuilder` assigns each chunk a section-local index;
        this overwrites it with the chunk's position across the whole
        document, now that all sections have been combined in order.

        Args:
            chunks: All chunks for the document, in final order.
        """
        for index, chunk in enumerate(chunks):
            chunk.metadata.chunk_index = index

    def _resolve_document_id(self, layout_document: LayoutDocument) -> str:
        """Resolves the document id to stamp on every chunk.

        `LayoutDocument` has no `document_id` field of its own; that
        identity is owned by the ingestion pipeline's metadata
        extraction stage. `pipeline.py` is expected to copy it into
        `layout_document.metadata["document_id"]` before chunking, so
        chunk, embedding, and vector-store records all share one id
        for the same source document.

        Args:
            layout_document: The document being chunked.

        Returns:
            The document id from `layout_document.metadata` if present;
            otherwise a deterministic fallback id derived from the
            document name, with a warning logged since it will not
            match the id used elsewhere in the pipeline.
        """
        document_id = layout_document.metadata.get("document_id")
        if document_id:
            return document_id

        logger.warning(
            "No document_id found in layout_document.metadata for '%s'; "
            "falling back to a name-derived id. Chunk ids may not match "
            "this document's metadata/embedding records elsewhere in the "
            "pipeline.",
            layout_document.document_name,
        )
        return uuid.uuid5(
            uuid.NAMESPACE_DNS, layout_document.document_name
        ).hex