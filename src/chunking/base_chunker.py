"""
OmniBrain - Chunking Engine

Module: Base Chunker

Purpose:
    Define the abstract contract every chunker implementation must
    follow: given a `LayoutDocument`, produce a `ChunkCollection`.

    This module contains no chunking logic itself. `LayoutChunker` is
    the current concrete implementation; future chunkers for other
    source formats (Markdown, HTML, DOCX) implement the same contract
    so the rest of the pipeline (validation, embedding) never needs to
    know which one produced a given `ChunkCollection`.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from ..models.chunk_models import ChunkCollection
from ..models.layout_models import LayoutDocument


class BaseChunker(ABC):
    """Abstract base class for all chunkers.

    Any concrete chunker takes a fully processed `LayoutDocument`
    (extracted, classified, ordered, related, sectioned, and
    validated) and returns a `ChunkCollection`.
    """

    @abstractmethod
    def chunk_document(self, layout_document: LayoutDocument) -> ChunkCollection:
        """Chunks a document.

        Args:
            layout_document: A fully processed `LayoutDocument`.

        Returns:
            A `ChunkCollection` containing every chunk produced for
            this document.
        """
        raise NotImplementedError

    @staticmethod
    def _generate_chunk_id() -> str:
        """Generates a globally unique identifier for a chunk.

        Shared across all `BaseChunker` implementations so chunk ids
        are consistently formatted regardless of which concrete
        chunker produced them, matching the id scheme already used by
        `LayoutExtractor` and `SectionBuilder`.

        Returns:
            A UUID4 hex string.
        """
        return uuid.uuid4().hex