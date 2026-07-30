"""
OmniBrain - Chunking Engine

Module: Chunk Validator

Purpose:
    Check a fully assembled `ChunkCollection` for quality problems —
    empty chunks, duplicate chunks, broken traceability metadata — and
    report size-distribution statistics. Follows the same philosophy
    as `preprocessing/layout/validator.py`: remove genuinely broken
    entries, but never rewrite content to force it to fit a size
    target, since chunk boundaries are `SemanticBuilder`'s decision to
    make, not this module's to second-guess.

    This module does not build, order, or section chunks. It only
    audits and cleans the `ChunkCollection` produced by
    `LayoutChunker`.
"""

from __future__ import annotations

import logging

from configs.settings import Settings

from ..models.chunk_models import (
    Chunk,
    ChunkCollection,
    ChunkCollectionStatistics,
    ChunkType,
)

logger = logging.getLogger(__name__)


class ChunkValidator:
    """Validates and cleans a fully assembled `ChunkCollection`.

    Removes empty chunks, duplicate chunks, and chunks with broken
    traceability metadata. Flags (but never removes or alters) chunks
    outside the configured size range, since size is a byproduct of
    `SemanticBuilder`'s decisions, not something this module corrects.
    """

    def validate(self, collection: ChunkCollection) -> ChunkCollection:
        """Validates and cleans a chunk collection in place.

        Args:
            collection: A `ChunkCollection` assembled by
                `LayoutChunker`.

        Returns:
            The same `ChunkCollection` instance, with invalid chunks
            removed, remaining chunks renumbered contiguously, and
            `statistics` populated.
        """
        logger.info(
            "Validating chunk collection for document: %s",
            collection.document_name,
        )

        chunks, empty_removed = self._remove_empty_chunks(collection.chunks)
        chunks, duplicate_removed = self._remove_duplicate_chunks(chunks)
        chunks, integrity_removed = self._remove_integrity_failures(chunks)

        oversized_count = self._count_oversized(chunks)
        undersized_count = self._count_undersized(chunks)

        self._renumber_chunks(chunks)
        collection.chunks = chunks

        collection.statistics = self._build_statistics(
            chunks,
            empty_removed=empty_removed,
            duplicate_removed=duplicate_removed,
            integrity_removed=integrity_removed,
            oversized_count=oversized_count,
            undersized_count=undersized_count,
        )

        logger.info(
            "Validation complete for '%s': %d chunk(s) remain",
            collection.document_name,
            len(chunks),
        )

        return collection

    def _remove_empty_chunks(
        self, chunks: list[Chunk]
    ) -> tuple[list[Chunk], int]:
        """Drops chunks whose rendered text is empty or whitespace-only.

        Args:
            chunks: Chunks to check.

        Returns:
            A tuple of (kept chunks, number removed).
        """
        kept: list[Chunk] = []
        removed = 0

        for chunk in chunks:
            if chunk.text.strip():
                kept.append(chunk)
            else:
                removed += 1
                logger.warning("Dropping empty chunk: %s", chunk.id)

        return kept, removed

    def _remove_duplicate_chunks(
        self, chunks: list[Chunk]
    ) -> tuple[list[Chunk], int]:
        """Drops chunks with a duplicate id or duplicate exact text.

        A colliding id is always a bug (e.g. two chunks generated with
        the same identifier). Duplicate exact text within the same
        document most often indicates degenerate section chunking
        (e.g. a section producing two chunks that ended up byte-for-
        byte identical); ordinary chunk overlap does not trigger this,
        since overlapping chunks share only part of their text, not
        all of it.

        Args:
            chunks: Chunks to check, in their current order.

        Returns:
            A tuple of (kept chunks, number removed). The first
            occurrence of any duplicate is kept.
        """
        seen_ids: set[str] = set()
        seen_fingerprints: set[tuple[str, str]] = set()
        kept: list[Chunk] = []
        removed = 0

        for chunk in chunks:
            if chunk.id in seen_ids:
                removed += 1
                logger.warning(
                    "Dropping chunk with duplicate id: %s", chunk.id
                )
                continue

            fingerprint = (chunk.document_id, chunk.text)
            if fingerprint in seen_fingerprints:
                removed += 1
                logger.warning(
                    "Dropping chunk %s: duplicate content of an earlier "
                    "chunk",
                    chunk.id,
                )
                continue

            seen_ids.add(chunk.id)
            seen_fingerprints.add(fingerprint)
            kept.append(chunk)

        return kept, removed

    def _remove_integrity_failures(
        self, chunks: list[Chunk]
    ) -> tuple[list[Chunk], int]:
        """Drops chunks whose traceability metadata is broken.

        Args:
            chunks: Chunks to check.

        Returns:
            A tuple of (kept chunks, number removed).
        """
        kept: list[Chunk] = []
        removed = 0

        for chunk in chunks:
            if self._has_valid_metadata(chunk):
                kept.append(chunk)
            else:
                removed += 1
                logger.warning(
                    "Dropping chunk %s: failed metadata integrity check",
                    chunk.id,
                )

        return kept, removed

    def _has_valid_metadata(self, chunk: Chunk) -> bool:
        """Checks whether a chunk's traceability metadata is coherent.

        Args:
            chunk: The chunk to check.

        Returns:
            True if the chunk has a document id, at least one source
            element id (chunking Rule 7 requires traceability), and
            internally consistent page and reading-order ranges.
        """
        metadata = chunk.metadata

        if not chunk.document_id or not metadata.document_id:
            return False

        if not metadata.element_ids:
            return False

        if metadata.page_start > metadata.page_end:
            return False

        has_reading_order = (
            metadata.reading_order_start != -1
            and metadata.reading_order_end != -1
        )
        if has_reading_order and metadata.reading_order_start > metadata.reading_order_end:
            return False

        return True

    def _count_oversized(self, chunks: list[Chunk]) -> int:
        """Counts chunks whose text exceeds the configured maximum size.

        Informational only: an oversized chunk is expected whenever a
        single element (a large paragraph, a large table) exceeds
        `Settings.MAX_CHUNK_SIZE` on its own, since chunking Rule 6
        forbids splitting it. This count is never used to remove or
        alter a chunk.

        Args:
            chunks: Chunks to check.

        Returns:
            The number of chunks exceeding `Settings.MAX_CHUNK_SIZE`.
        """
        return sum(
            1 for chunk in chunks if chunk.statistics.char_count > Settings.MAX_CHUNK_SIZE
        )

    def _count_undersized(self, chunks: list[Chunk]) -> int:
        """Counts non-table chunks smaller than the configured minimum size.

        Table chunks are exempt: chunking Rule 4 keeps a table intact
        regardless of size, so a small table is expected and not a
        quality problem.

        Args:
            chunks: Chunks to check.

        Returns:
            The number of non-table chunks below `Settings.
            MIN_CHUNK_SIZE`.
        """
        return sum(
            1
            for chunk in chunks
            if chunk.chunk_type != ChunkType.TABLE
            and chunk.statistics.char_count < Settings.MIN_CHUNK_SIZE
        )

    def _renumber_chunks(self, chunks: list[Chunk]) -> None:
        """Reassigns a contiguous chunk index after removals, in place.

        Removing chunks during validation leaves gaps in the index
        `LayoutChunker` assigned; this closes them so the final
        collection's indices run 0..n-1 with no gaps.

        Args:
            chunks: The chunks remaining after all removal checks.
        """
        for index, chunk in enumerate(chunks):
            chunk.metadata.chunk_index = index

    def _build_statistics(
        self,
        chunks: list[Chunk],
        empty_removed: int,
        duplicate_removed: int,
        integrity_removed: int,
        oversized_count: int,
        undersized_count: int,
    ) -> ChunkCollectionStatistics:
        """Builds the aggregate statistics block for a validated collection.

        Args:
            chunks: The final, validated chunks.
            empty_removed: Count from `_remove_empty_chunks`.
            duplicate_removed: Count from `_remove_duplicate_chunks`.
            integrity_removed: Count from `_remove_integrity_failures`.
            oversized_count: Count from `_count_oversized`.
            undersized_count: Count from `_count_undersized`.

        Returns:
            A populated `ChunkCollectionStatistics`.
        """
        if not chunks:
            return ChunkCollectionStatistics(
                empty_chunks_removed=empty_removed,
                duplicate_chunks_removed=duplicate_removed,
                integrity_failures_removed=integrity_removed,
            )

        char_counts = [chunk.statistics.char_count for chunk in chunks]
        table_chunk_count = sum(
            1 for chunk in chunks if chunk.chunk_type == ChunkType.TABLE
        )

        return ChunkCollectionStatistics(
            total_chunks=len(chunks),
            total_characters=sum(char_counts),
            total_words=sum(chunk.statistics.word_count for chunk in chunks),
            average_chunk_size=round(sum(char_counts) / len(char_counts), 2),
            smallest_chunk_size=min(char_counts),
            largest_chunk_size=max(char_counts),
            table_chunks=table_chunk_count,
            empty_chunks_removed=empty_removed,
            duplicate_chunks_removed=duplicate_removed,
            integrity_failures_removed=integrity_removed,
            oversized_chunks_flagged=oversized_count,
            undersized_chunks_flagged=undersized_count,
        )