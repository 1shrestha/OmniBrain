"""
OmniBrain - Layout Parsing Engine

Module: Relationships

Purpose:
    Detect relationships between already-classified, already-ordered
    layout elements: heading-to-paragraph ownership, caption-to-media
    association, list item grouping, and paragraph continuation across
    column or page breaks.

    This module does not classify elements, determine reading order,
    or build the document's section hierarchy. It only produces a flat
    graph of `ElementRelationship` edges for `section_builder.py` to
    consume.

Relationship direction convention:
    Every `ElementRelationship(source_id, target_id, relationship)`
    reads as "source `relationship` target", e.g. a heading element as
    source with `RelationshipType.PARENT` and a paragraph as target
    means "the heading is the parent of the paragraph". A caption
    element as source with `RelationshipType.CAPTION_OF` and an image
    as target means "the caption is the caption of the image".
"""

from __future__ import annotations

import logging

from ...models.layout_models import (
    ElementRelationship,
    ElementType,
    LayoutDocument,
    LayoutElement,
    LayoutPage,
    RelationshipType,
)

logger = logging.getLogger(__name__)

# Element types that introduce a new logical section and can "own"
# subsequent content until the next heading-like element.
_HEADING_TYPES = frozenset(
    {ElementType.TITLE, ElementType.HEADING, ElementType.SUBTITLE}
)

# Element types that can be owned by a preceding heading.
_OWNABLE_CONTENT_TYPES = frozenset(
    {
        ElementType.PARAGRAPH,
        ElementType.LIST,
        ElementType.TABLE,
        ElementType.IMAGE,
        ElementType.CODE,
        ElementType.FORMULA,
    }
)

# Element types that a caption can be describing.
_MEDIA_TYPES = frozenset({ElementType.IMAGE, ElementType.TABLE})

# Punctuation that plausibly ends a sentence. A paragraph not ending in
# one of these is a candidate for continuing into the next paragraph
# element.
_SENTENCE_TERMINATORS = frozenset({".", "!", "?", ":", ";", '"', "'"})

# Maximum font size difference, in points, still considered "the same
# font" when checking whether two paragraph fragments plausibly belong
# to the same run of body text.
_FONT_SIZE_TOLERANCE = 0.5


class RelationshipDetector:
    """Detects relationships between classified, ordered elements.

    Produces a flat list of `ElementRelationship` edges covering
    heading ownership, caption association, list grouping, and
    paragraph continuation. Does not build a hierarchy itself.
    """

    def detect_relationships(self, document: LayoutDocument) -> LayoutDocument:
        """Detects all relationships for a document.

        Args:
            document: A `LayoutDocument` with classified elements in
                reading order (i.e. already processed by
                `ReadingOrderResolver`).

        Returns:
            The same `LayoutDocument` instance, with `relationships`
            populated.
        """
        logger.info(
            "Detecting relationships for document: %s", document.document_name
        )

        ordered_elements = self._flatten_in_reading_order(document)

        relationships: list[ElementRelationship] = []
        relationships.extend(
            self._detect_heading_ownership(ordered_elements)
        )
        relationships.extend(self._detect_caption_relationships(document))
        relationships.extend(self._detect_list_relationships(ordered_elements))
        relationships.extend(
            self._detect_paragraph_continuations(ordered_elements)
        )

        document.relationships = relationships

        logger.info("Detected %d relationship(s)", len(relationships))

        return document

    def _flatten_in_reading_order(
        self, document: LayoutDocument
    ) -> list[LayoutElement]:
        """Flattens a document's pages into a single reading-order sequence.

        Args:
            document: A `LayoutDocument` whose pages are already
                internally sorted in reading order.

        Returns:
            All elements across all pages, concatenated in page order.
        """
        pages_in_order = sorted(document.pages, key=lambda page: page.page_number)
        return [element for page in pages_in_order for element in page.elements]

    def _detect_heading_ownership(
        self, elements: list[LayoutElement]
    ) -> list[ElementRelationship]:
        """Links each heading-like element to the content it owns.

        Walks the reading-order sequence, tracking the most recent
        heading-like element, and links it as the parent of every
        ownable content element until the next heading-like element is
        reached.

        Args:
            elements: All elements in document reading order.

        Returns:
            `PARENT` relationships from headings to their content.
        """
        relationships: list[ElementRelationship] = []
        current_heading: LayoutElement | None = None

        for element in elements:
            if element.element_type in _HEADING_TYPES:
                current_heading = element
                continue

            if current_heading is None:
                continue

            if element.element_type in _OWNABLE_CONTENT_TYPES:
                relationships.append(
                    ElementRelationship(
                        source_id=current_heading.id,
                        target_id=element.id,
                        relationship=RelationshipType.PARENT,
                    )
                )

        return relationships

    def _detect_caption_relationships(
        self, document: LayoutDocument
    ) -> list[ElementRelationship]:
        """Links each caption to the image or table it describes.

        Args:
            document: A `LayoutDocument` with classified elements.

        Returns:
            `CAPTION_OF` relationships from captions to media elements.
        """
        relationships: list[ElementRelationship] = []

        for page in document.pages:
            relationships.extend(self._detect_captions_on_page(page))

        return relationships

    def _detect_captions_on_page(
        self, page: LayoutPage
    ) -> list[ElementRelationship]:
        """Links captions to media elements within a single page.

        Args:
            page: A `LayoutPage` with elements in reading order.

        Returns:
            `CAPTION_OF` relationships found on this page.
        """
        relationships: list[ElementRelationship] = []
        elements = page.elements

        for index, element in enumerate(elements):
            if element.element_type != ElementType.CAPTION:
                continue

            target = self._find_nearest_media_element(elements, index)
            if target is not None:
                relationships.append(
                    ElementRelationship(
                        source_id=element.id,
                        target_id=target.id,
                        relationship=RelationshipType.CAPTION_OF,
                    )
                )

        return relationships

    def _find_nearest_media_element(
        self, elements: list[LayoutElement], caption_index: int
    ) -> LayoutElement | None:
        """Finds the image or table adjacent to a caption in reading order.

        A caption may appear immediately before or immediately after
        its media element (e.g. a caption above a table versus below a
        figure). When both neighbors are media elements, the vertically
        closer one is chosen.

        Args:
            elements: All elements on the caption's page, in reading
                order.
            caption_index: Index of the caption element within
                `elements`.

        Returns:
            The associated media `LayoutElement`, or `None` if neither
            neighbor is an image or table.
        """
        caption = elements[caption_index]
        candidates = []

        if caption_index > 0:
            previous_element = elements[caption_index - 1]
            if previous_element.element_type in _MEDIA_TYPES:
                candidates.append(previous_element)

        if caption_index < len(elements) - 1:
            next_element = elements[caption_index + 1]
            if next_element.element_type in _MEDIA_TYPES:
                candidates.append(next_element)

        if not candidates:
            return None

        return min(
            candidates,
            key=lambda candidate: self._vertical_distance(caption, candidate),
        )

    def _vertical_distance(
        self, first: LayoutElement, second: LayoutElement
    ) -> float:
        """Computes the vertical gap between two elements' bounding boxes.

        Args:
            first: The first element.
            second: The second element.

        Returns:
            The absolute gap between the nearer edges of the two
            bounding boxes. Returns `float("inf")` if either element
            lacks a bounding box.
        """
        if first.bbox is None or second.bbox is None:
            return float("inf")

        if first.bbox.y0 <= second.bbox.y0:
            return max(0.0, second.bbox.y0 - first.bbox.y1)

        return max(0.0, first.bbox.y0 - second.bbox.y1)

    def _detect_list_relationships(
        self, elements: list[LayoutElement]
    ) -> list[ElementRelationship]:
        """Groups consecutive list-item elements into a single list.

        Runs of adjacent `LIST`-classified elements on the same page
        are treated as one logical list: the first item anchors the
        group, subsequent items are marked `PART_OF` it, and
        consecutive items are chained with `NEXT`.

        Args:
            elements: All elements in document reading order.

        Returns:
            `PART_OF` and `NEXT` relationships describing list
            grouping.
        """
        relationships: list[ElementRelationship] = []
        index = 0

        while index < len(elements):
            if elements[index].element_type != ElementType.LIST:
                index += 1
                continue

            group_end = self._find_list_group_end(elements, index)
            group = elements[index:group_end]
            relationships.extend(self._link_list_group(group))
            index = group_end

        return relationships

    def _find_list_group_end(
        self, elements: list[LayoutElement], start: int
    ) -> int:
        """Finds the exclusive end index of a run of list elements.

        Args:
            elements: All elements in document reading order.
            start: Index of the first `LIST` element in the run.

        Returns:
            The index one past the last consecutive `LIST` element on
            the same page as `start`.
        """
        page_number = elements[start].page_number
        end = start + 1

        while (
            end < len(elements)
            and elements[end].element_type == ElementType.LIST
            and elements[end].page_number == page_number
        ):
            end += 1

        return end

    def _link_list_group(
        self, group: list[LayoutElement]
    ) -> list[ElementRelationship]:
        """Builds relationships linking a single run of list items.

        Args:
            group: Consecutive `LIST` elements forming one list. Must
                contain at least one element.

        Returns:
            `PART_OF` edges from each item to the group's anchor item,
            and `NEXT` edges chaining consecutive items. Empty if the
            group has fewer than two items.
        """
        if len(group) < 2:
            return []

        anchor = group[0]
        relationships = [
            ElementRelationship(
                source_id=item.id,
                target_id=anchor.id,
                relationship=RelationshipType.PART_OF,
            )
            for item in group[1:]
        ]
        relationships.extend(
            ElementRelationship(
                source_id=current.id,
                target_id=following.id,
                relationship=RelationshipType.NEXT,
            )
            for current, following in zip(group, group[1:])
        )

        return relationships

    def _detect_paragraph_continuations(
        self, elements: list[LayoutElement]
    ) -> list[ElementRelationship]:
        """Detects paragraphs split across a column or page break.

        Args:
            elements: All elements in document reading order.

        Returns:
            `NEXT` relationships linking a paragraph fragment to its
            continuation.
        """
        relationships: list[ElementRelationship] = []

        for current, following in zip(elements, elements[1:]):
            if current.element_type != ElementType.PARAGRAPH:
                continue
            if following.element_type != ElementType.PARAGRAPH:
                continue

            if self._looks_like_continuation(current, following):
                relationships.append(
                    ElementRelationship(
                        source_id=current.id,
                        target_id=following.id,
                        relationship=RelationshipType.NEXT,
                    )
                )

        return relationships

    def _looks_like_continuation(
        self, first: LayoutElement, second: LayoutElement
    ) -> bool:
        """Checks whether one paragraph plausibly continues into the next.

        A fragment is treated as continuing if the first doesn't end
        with sentence-ending punctuation, the second starts with a
        lowercase letter, and their fonts match closely enough to
        suggest the same run of body text.

        Args:
            first: The earlier paragraph in reading order.
            second: The later paragraph in reading order.

        Returns:
            True if the pair looks like a single paragraph split across
            a column or page break.
        """
        first_text = first.text.rstrip()
        second_text = second.text.lstrip()
        if not first_text or not second_text:
            return False

        ends_without_terminator = first_text[-1] not in _SENTENCE_TERMINATORS
        starts_lowercase = second_text[0].islower()

        return (
            ends_without_terminator
            and starts_lowercase
            and self._fonts_plausibly_match(first, second)
        )

    def _fonts_plausibly_match(
        self, first: LayoutElement, second: LayoutElement
    ) -> bool:
        """Checks whether two elements' fonts are consistent with one run of text.

        Args:
            first: The earlier element.
            second: The later element.

        Returns:
            True if either element lacks font info (lenient default),
            or if both share the same font name and a size within
            `_FONT_SIZE_TOLERANCE`.
        """
        if first.font is None or second.font is None:
            return True

        same_name = first.font.name == second.font.name
        similar_size = (
            abs(first.font.size - second.font.size) <= _FONT_SIZE_TOLERANCE
        )

        return same_name and similar_size