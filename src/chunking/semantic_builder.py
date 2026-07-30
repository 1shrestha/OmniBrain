"""
OmniBrain - Chunking Engine

Module: Semantic Builder

Purpose:
    Build semantically coherent chunks from a single `LayoutSection`.
    This is where every chunking design rule is enforced: a chunk
    never spans two sections, a heading stays with its first
    paragraph, captions stay fused to their image or table, tables are
    never split, reading order is preserved exactly, chunks are
    complete semantic units rather than character windows, and every
    chunk carries full traceability metadata.

    This module does not iterate a whole document, orchestrate
    validation, or decide which sections to process — that is
    `layout_chunker.py`'s job. `SemanticBuilder` only knows how to turn
    one section's elements into chunks.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from configs.settings import Settings

from ..models.chunk_models import (
    Chunk,
    ChunkMetadata,
    ChunkStatistics,
    ChunkType,
)
from ..models.layout_models import (
    ElementRelationship,
    ElementType,
    LayoutElement,
    LayoutSection,
    RelationshipType,
)


@dataclass
class _PendingChunk:
    """A chunk still being assembled, before metadata is finalized."""

    elements: list[LayoutElement] = field(default_factory=list)
    chunk_type: ChunkType = ChunkType.SEMANTIC


class SemanticBuilder:
    """Builds chunks from a single section's elements.

    Fuses captions with their media, keeps tables intact as their own
    chunks, accumulates ordinary content up to a configured target
    size without splitting elements, carries whole-element overlap
    between consecutive chunks, and folds the section heading into the
    first chunk's text.
    """

    def build_section_chunks(
        self,
        document_id: str,
        document_name: str,
        source_path: str,
        section: LayoutSection,
        relationships: list[ElementRelationship],
    ) -> list[Chunk]:
        """Builds all chunks for a single section.

        Args:
            document_id: Id of the document this section belongs to.
            document_name: Human-readable document name.
            source_path: Path to the source PDF, for traceability.
            section: The `LayoutSection` to chunk.
            relationships: All relationships detected for the document.
                Only `CAPTION_OF` relationships fully contained within
                this section are used.

        Returns:
            Chunks for this section, in reading order. Empty if the
            section has neither a heading nor any elements.
        """
        if section.heading is None and not section.elements:
            return []

        elements_by_id = {element.id: element for element in section.elements}
        fusion_map = self._build_caption_fusion_map(section, relationships)
        units = self._group_into_units(
            section.elements, elements_by_id, fusion_map
        )

        pending_chunks = self._accumulate_units(units)
        pending_chunks = self._attach_heading(pending_chunks, section)

        return [
            self._finalize_chunk(
                document_id, document_name, source_path, section, index, pending
            )
            for index, pending in enumerate(pending_chunks)
        ]

    def _build_caption_fusion_map(
        self,
        section: LayoutSection,
        relationships: list[ElementRelationship],
    ) -> dict[str, str]:
        """Maps caption/media element ids to their fusion partner's id.

        Only `CAPTION_OF` relationships where both endpoints belong to
        this section are used (chunking Rule 1 forbids a chunk from
        spanning sections, so a caption-media pair split across
        sections cannot be fused).

        Args:
            section: The section being chunked.
            relationships: All relationships detected for the document.

        Returns:
            A mapping from element id to its fusion partner's id, in
            both directions.
        """
        section_element_ids = {element.id for element in section.elements}
        fusion_map: dict[str, str] = {}

        for relationship in relationships:
            if relationship.relationship != RelationshipType.CAPTION_OF:
                continue
            if (
                relationship.source_id in section_element_ids
                and relationship.target_id in section_element_ids
            ):
                fusion_map[relationship.source_id] = relationship.target_id
                fusion_map[relationship.target_id] = relationship.source_id

        return fusion_map

    def _group_into_units(
        self,
        elements: list[LayoutElement],
        elements_by_id: dict[str, LayoutElement],
        fusion_map: dict[str, str],
    ) -> list[list[LayoutElement]]:
        """Groups section elements into logical, indivisible units.

        A fused caption/media pair becomes a single two-element unit,
        ordered by reading order so a caption appearing before or
        after its media both render naturally. Every other element is
        its own single-element unit. Overall reading order is
        preserved: `elements` is already reading-order sorted.

        Args:
            elements: The section's content elements, in reading order.
            elements_by_id: Lookup of the same elements by id.
            fusion_map: Caption/media fusion pairs, from
                `_build_caption_fusion_map`.

        Returns:
            Units in reading order.
        """
        units: list[list[LayoutElement]] = []
        consumed_ids: set[str] = set()

        for element in elements:
            if element.id in consumed_ids:
                continue

            partner_id = fusion_map.get(element.id)
            partner = elements_by_id.get(partner_id) if partner_id else None

            if partner is not None and partner.id not in consumed_ids:
                pair = sorted([element, partner], key=lambda e: e.reading_order)
                units.append(pair)
                consumed_ids.add(element.id)
                consumed_ids.add(partner.id)
                continue

            units.append([element])
            consumed_ids.add(element.id)

        return units

    def _accumulate_units(
        self, units: list[list[LayoutElement]]
    ) -> list[_PendingChunk]:
        """Accumulates units into chunks without ever splitting a unit.

        Table units (chunking Rule 4) always become their own
        dedicated chunk. Other units accumulate into a running chunk
        until adding the next unit would exceed `Settings.
        MAX_CHUNK_SIZE` and the chunk has already reached `Settings.
        MIN_CHUNK_SIZE`; whole trailing elements are then carried
        forward as overlap into the next chunk.

        Args:
            units: Logical units in reading order, from
                `_group_into_units`.

        Returns:
            Assembled chunks, in reading order.
        """
        pending_chunks: list[_PendingChunk] = []
        current_elements: list[LayoutElement] = []

        for unit in units:
            if self._unit_is_table(unit):
                self._flush_current(pending_chunks, current_elements)
                current_elements = []
                pending_chunks.append(
                    _PendingChunk(elements=list(unit), chunk_type=ChunkType.TABLE)
                )
                continue

            current_elements = self._append_unit(
                pending_chunks, current_elements, unit
            )

        self._flush_current(pending_chunks, current_elements)

        return pending_chunks

    def _append_unit(
        self,
        pending_chunks: list[_PendingChunk],
        current_elements: list[LayoutElement],
        unit: list[LayoutElement],
    ) -> list[LayoutElement]:
        """Adds one non-table unit to the running chunk, splitting if needed.

        Args:
            pending_chunks: Chunks already finalized, appended to
                in place if a split occurs.
            current_elements: Elements accumulated so far for the
                chunk being built.
            unit: The next unit to add.

        Returns:
            The (possibly reset) running list of elements after adding
            `unit`.
        """
        current_length = self._elements_text_length(current_elements)
        candidate_length = current_length + self._elements_text_length(unit)

        exceeds_max = candidate_length > Settings.MAX_CHUNK_SIZE
        meets_minimum = current_length >= Settings.MIN_CHUNK_SIZE

        if current_elements and exceeds_max and meets_minimum:
            overlap_elements = self._compute_overlap(current_elements)
            self._flush_current(pending_chunks, current_elements)
            current_elements = list(overlap_elements)

        current_elements.extend(unit)
        return current_elements

    def _unit_is_table(self, unit: list[LayoutElement]) -> bool:
        """Checks whether a unit contains a table element.

        Args:
            unit: A logical unit, one or two elements.

        Returns:
            True if any element in the unit is a `TABLE`.
        """
        return any(element.element_type == ElementType.TABLE for element in unit)

    def _elements_text_length(self, elements: list[LayoutElement]) -> int:
        """Estimates the rendered text length of a list of elements.

        Args:
            elements: Elements to measure.

        Returns:
            Approximate combined character count, including rendered
            table content.
        """
        return sum(len(self._render_element_text(element)) for element in elements)

    def _flush_current(
        self,
        pending_chunks: list[_PendingChunk],
        current_elements: list[LayoutElement],
    ) -> None:
        """Closes out the running chunk, if it has any content.

        Args:
            pending_chunks: Chunks already finalized, appended to in
                place.
            current_elements: Elements accumulated for the chunk being
                closed.
        """
        if current_elements:
            pending_chunks.append(
                _PendingChunk(
                    elements=list(current_elements), chunk_type=ChunkType.SEMANTIC
                )
            )

    def _compute_overlap(
        self, elements: list[LayoutElement]
    ) -> list[LayoutElement]:
        """Selects trailing whole elements to carry into the next chunk.

        Walks backward from the end of a just-closed chunk, including
        whole elements until `Settings.CHUNK_OVERLAP` characters would
        be exceeded. At least one element is always included when
        overlap is enabled, even if it alone exceeds the target, since
        elements are never split (chunking Rule 6).

        Args:
            elements: The elements of the chunk being closed.

        Returns:
            The trailing elements to prepend to the next chunk. Empty
            if `Settings.CHUNK_OVERLAP` is zero or negative.
        """
        if Settings.CHUNK_OVERLAP <= 0:
            return []

        overlap: list[LayoutElement] = []
        accumulated_length = 0

        for element in reversed(elements):
            element_length = len(self._render_element_text(element))
            if accumulated_length and (
                accumulated_length + element_length > Settings.CHUNK_OVERLAP
            ):
                break

            overlap.insert(0, element)
            accumulated_length += element_length

        return overlap

    def _attach_heading(
        self, pending_chunks: list[_PendingChunk], section: LayoutSection
    ) -> list[_PendingChunk]:
        """Folds the section heading into the first chunk's text.

        Implements chunking Rule 2: a heading is never left isolated
        from its first paragraph. If the section has no heading, the
        chunks are returned unchanged. If the first chunk is a table,
        the heading is placed in its own small chunk immediately
        before it instead of being folded into the table, so the
        table chunk's content and type remain purely tabular.

        Args:
            pending_chunks: Chunks assembled for the section.
            section: The section, for its `heading` element.

        Returns:
            Chunks with the heading incorporated.
        """
        if section.heading is None:
            return pending_chunks

        if not pending_chunks:
            return [_PendingChunk(elements=[section.heading])]

        first_chunk = pending_chunks[0]
        if first_chunk.chunk_type == ChunkType.TABLE:
            heading_chunk = _PendingChunk(elements=[section.heading])
            return [heading_chunk, *pending_chunks]

        first_chunk.elements = [section.heading, *first_chunk.elements]
        return pending_chunks

    def _finalize_chunk(
        self,
        document_id: str,
        document_name: str,
        source_path: str,
        section: LayoutSection,
        index: int,
        pending: _PendingChunk,
    ) -> Chunk:
        """Converts an assembled `_PendingChunk` into a finished `Chunk`.

        Args:
            document_id: Id of the document.
            document_name: Human-readable document name.
            source_path: Path to the source PDF.
            section: The section this chunk belongs to.
            index: Section-local position of this chunk. `layout_chunker`
                is responsible for any document-wide renumbering.
            pending: The assembled elements and chunk type.

        Returns:
            A fully populated `Chunk`.
        """
        text = self._render_text(pending.elements)
        metadata = self._build_metadata(
            document_id, document_name, source_path, section, index, pending
        )
        statistics = self._build_statistics(pending.elements, text)

        return Chunk(
            id=self._generate_chunk_id(),
            document_id=document_id,
            text=text,
            metadata=metadata,
            statistics=statistics,
            chunk_type=pending.chunk_type,
        )

    def _render_text(self, elements: list[LayoutElement]) -> str:
        """Renders a chunk's elements into a single text block.

        Args:
            elements: The chunk's constituent elements, in order.

        Returns:
            Element texts joined by blank lines, skipping any element
            that renders to empty text.
        """
        rendered = (self._render_element_text(element) for element in elements)
        return "\n\n".join(text for text in rendered if text)

    def _render_element_text(self, element: LayoutElement) -> str:
        """Renders a single element's text content.

        Tables carry no `text` of their own (`extractor.py` leaves it
        empty); their cell data lives in `metadata["cells"]` and is
        rendered here into a tab-separated block so a table chunk
        still has meaningful text for embedding. Every other element
        type is rendered as its stripped `text`.

        Args:
            element: The element to render.

        Returns:
            The element's rendered text, possibly empty.
        """
        if element.element_type == ElementType.TABLE:
            return self._render_table_text(element)

        return element.text.strip()

    def _render_table_text(self, element: LayoutElement) -> str:
        """Renders a table element's cell data as tab-separated rows.

        Args:
            element: A `TABLE` element with `metadata["cells"]` set by
                `extractor.py`.

        Returns:
            Rows joined by newlines, cells within a row joined by
            tabs. Empty if no cell data is present.
        """
        rows = element.metadata.get("cells", [])
        if not rows:
            return ""

        rendered_rows = [
            "\t".join("" if cell is None else str(cell) for cell in row)
            for row in rows
        ]
        return "\n".join(rendered_rows)

    def _build_metadata(
        self,
        document_id: str,
        document_name: str,
        source_path: str,
        section: LayoutSection,
        index: int,
        pending: _PendingChunk,
    ) -> ChunkMetadata:
        """Builds the traceability metadata for a finished chunk.

        Args:
            document_id: Id of the document.
            document_name: Human-readable document name.
            source_path: Path to the source PDF.
            section: The section this chunk belongs to.
            index: Section-local position of this chunk.
            pending: The assembled elements and chunk type.

        Returns:
            A populated `ChunkMetadata`.
        """
        page_numbers = [element.page_number for element in pending.elements]
        reading_orders = [
            element.reading_order
            for element in pending.elements
            if element.reading_order >= 0
        ]

        return ChunkMetadata(
            document_id=document_id,
            document_name=document_name,
            source_path=source_path,
            section_id=section.id,
            section_title=section.title,
            section_level=section.level,
            heading_text=section.heading.text if section.heading else None,
            page_start=min(page_numbers) if page_numbers else 0,
            page_end=max(page_numbers) if page_numbers else 0,
            reading_order_start=min(reading_orders) if reading_orders else -1,
            reading_order_end=max(reading_orders) if reading_orders else -1,
            element_ids=[element.id for element in pending.elements],
            element_types=[
                element.element_type.value for element in pending.elements
            ],
            chunk_index=index,
        )

    def _build_statistics(
        self, elements: list[LayoutElement], text: str
    ) -> ChunkStatistics:
        """Computes size and content-flag statistics for a finished chunk.

        Args:
            elements: The chunk's constituent elements.
            text: The chunk's rendered text.

        Returns:
            A populated `ChunkStatistics`.
        """
        element_types = {element.element_type for element in elements}

        return ChunkStatistics(
            char_count=len(text),
            word_count=len(text.split()),
            element_count=len(elements),
            has_table=ElementType.TABLE in element_types,
            has_image=ElementType.IMAGE in element_types,
            has_code=ElementType.CODE in element_types,
            has_formula=ElementType.FORMULA in element_types,
        )

    @staticmethod
    def _generate_chunk_id() -> str:
        """Generates a globally unique identifier for a chunk.

        Returns:
            A UUID4 hex string.
        """
        return uuid.uuid4().hex