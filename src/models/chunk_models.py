"""
OmniBrain - Chunking Engine

Module: Chunk Models

Purpose:
    Define the core data models used throughout the chunking pipeline:
    individual chunks, their metadata and statistics, and the
    collection that groups them for a document.

    This module contains no chunking logic. It only defines the shape
    of the data that `semantic_builder.py`, `layout_chunker.py`, and
    `chunk_validator.py` produce, populate, and check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ==========================================================
# ENUMS
# ==========================================================


class ChunkType(str, Enum):
    """Kind of content a chunk represents.

    Distinguishes chunks that carry ordinary flowing prose from
    chunks built around content that must never be split apart (e.g.
    a table, per chunking Rule 4), and from chunks produced by the
    legacy fallback chunker rather than the layout-aware pipeline.
    """

    SEMANTIC = "semantic"
    TABLE = "table"
    FALLBACK = "fallback"


# ==========================================================
# CHUNK METADATA
# ==========================================================


@dataclass
class ChunkMetadata:
    """Provenance and structural context for a single chunk.

    Carries everything needed to trace a chunk back to the exact
    source elements, section, and pages it was built from (chunking
    Rule 7), plus the structural context (heading, section) that
    justified how it was formed.
    """

    document_id: str
    document_name: str
    source_path: str

    section_id: str | None = None
    section_title: str = ""
    section_level: int = 1

    heading_text: str | None = None

    page_start: int = 0
    page_end: int = 0

    reading_order_start: int = -1
    reading_order_end: int = -1

    element_ids: list[str] = field(default_factory=list)
    element_types: list[str] = field(default_factory=list)

    chunk_index: int = 0

    extraction_method: str = "layout"


# ==========================================================
# CHUNK STATISTICS
# ==========================================================


@dataclass
class ChunkStatistics:
    """Quantitative measures describing a single chunk's content."""

    char_count: int = 0
    word_count: int = 0
    element_count: int = 0

    has_table: bool = False
    has_image: bool = False
    has_code: bool = False
    has_formula: bool = False


# ==========================================================
# CHUNK
# ==========================================================


@dataclass
class Chunk:
    """A single semantic unit of chunked document content."""

    id: str
    document_id: str
    text: str

    metadata: ChunkMetadata

    statistics: ChunkStatistics = field(default_factory=ChunkStatistics)

    chunk_type: ChunkType = ChunkType.SEMANTIC


# ==========================================================
# CHUNK COLLECTION STATISTICS
# ==========================================================


@dataclass
class ChunkCollectionStatistics:
    """Aggregate statistics over an entire `ChunkCollection`.

    Populated by `chunk_validator.py` after validation, mirroring the
    statistics block `LayoutValidator` and the legacy `ChunkValidator`
    both produce.
    """

    total_chunks: int = 0
    total_characters: int = 0
    total_words: int = 0

    average_chunk_size: float = 0.0
    smallest_chunk_size: int = 0
    largest_chunk_size: int = 0

    table_chunks: int = 0

    empty_chunks_removed: int = 0
    duplicate_chunks_removed: int = 0
    integrity_failures_removed: int = 0
    oversized_chunks_flagged: int = 0
    undersized_chunks_flagged: int = 0


# ==========================================================
# CHUNK COLLECTION
# ==========================================================


@dataclass
class ChunkCollection:
    """All chunks produced for a single document.

    Analogous to `LayoutDocument` in the layout parsing pipeline: one
    instance per source document, carrying every chunk plus rollup
    statistics.
    """

    document_id: str
    document_name: str
    source_path: str

    chunks: list[Chunk] = field(default_factory=list)

    statistics: ChunkCollectionStatistics = field(
        default_factory=ChunkCollectionStatistics
    )

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_count(self) -> int:
        """Number of chunks currently in the collection.

        A derived view rather than a stored field, so it can never
        drift out of sync with `chunks` after validation removes or
        merges entries.
        """
        return len(self.chunks)