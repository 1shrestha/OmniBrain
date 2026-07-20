"""
OmniBrain - Layout Parsing Engine

Module: Validator

Purpose:
    Check the assembled layout for data-quality problems — missing
    (dangling) references, duplicate elements, empty text, invalid
    bounding boxes, and overlapping duplicate extractions — and return
    a cleaned `LayoutDocument`.

    This module does not extract, classify, order, relate, or section
    elements. It only audits and repairs the document produced by the
    rest of the pipeline.
"""

from __future__ import annotations

import logging

from ...models.layout_models import (
    BoundingBox,
    ElementType,
    LayoutDocument,
    LayoutElement,
    LayoutPage,
)

logger = logging.getLogger(__name__)

# Element types that legitimately have no text and must not be dropped
# by the empty-text check.
_TEXTLESS_TYPES = frozenset({ElementType.IMAGE, ElementType.TABLE})

# Bounding boxes are allowed to extend this many points beyond the
# page's nominal dimensions before being treated as invalid, to
# tolerate ordinary PDF rendering rounding.
_BBOX_TOLERANCE = 1.0

# Two elements are treated as duplicate extractions of the same
# content only if their bounding boxes overlap by at least this
# fraction (Intersection over Union) AND their type and text match
# exactly. This avoids flagging legitimate overlaps, such as a caption
# sitting on top of an image.
_DUPLICATE_IOU_THRESHOLD = 0.9


class LayoutValidator:
    """Validates and cleans a fully assembled layout document.

    Runs per-page element checks (invalid bounding boxes, empty text,
    duplicate ids, overlapping duplicate extractions), then repairs
    document-level referential integrity (relationships and sections
    that pointed at elements which were removed).
    """

    def validate_document(self, document: LayoutDocument) -> LayoutDocument:
        """Validates and cleans a document in place.

        Args:
            document: A fully assembled `LayoutDocument`.

        Returns:
            The same `LayoutDocument` instance, with invalid elements
            removed and dangling relationship/section references
            repaired.
        """
        logger.info("Validating document: %s", document.document_name)

        for page in document.pages:
            self._validate_page(page)

        self._remove_dangling_relationships(document)
        self._remove_dangling_section_references(document)

        logger.info("Validation complete for document: %s", document.document_name)

        return document

    def _validate_page(self, page: LayoutPage) -> None:
        """Runs all element-level checks on a single page, in place.

        Args:
            page: The `LayoutPage` to validate.
        """
        elements = page.elements
        elements = self._remove_invalid_bounding_boxes(elements, page)
        elements = self._remove_empty_text_elements(elements)
        elements = self._remove_duplicate_ids(elements)
        elements = self._remove_overlapping_duplicates(elements)

        page.elements = elements

    def _remove_invalid_bounding_boxes(
        self, elements: list[LayoutElement], page: LayoutPage
    ) -> list[LayoutElement]:
        """Drops elements with missing or geometrically invalid bounding boxes.

        Args:
            elements: Elements to check.
            page: The page they belong to, used to validate bounds.

        Returns:
            Elements whose bounding boxes are present and valid.
        """
        valid_elements = []

        for element in elements:
            if self._is_valid_bbox(element.bbox, page):
                valid_elements.append(element)
            else:
                logger.warning(
                    "Dropping element %s on page %d: invalid bounding box %s",
                    element.id,
                    page.page_number,
                    element.bbox,
                )

        return valid_elements

    def _is_valid_bbox(
        self, bbox: BoundingBox | None, page: LayoutPage
    ) -> bool:
        """Checks whether a bounding box is geometrically valid for its page.

        Args:
            bbox: The bounding box to check, possibly `None`.
            page: The page the bounding box should fit within.

        Returns:
            True if `bbox` is present, has positive width and height,
            and falls within the page bounds (with a small tolerance
            for rendering rounding).
        """
        if bbox is None:
            return False

        if bbox.width <= 0 or bbox.height <= 0:
            return False

        within_left_top = (
            bbox.x0 >= -_BBOX_TOLERANCE and bbox.y0 >= -_BBOX_TOLERANCE
        )
        within_right_bottom = (
            bbox.x1 <= page.width + _BBOX_TOLERANCE
            and bbox.y1 <= page.height + _BBOX_TOLERANCE
        )

        return within_left_top and within_right_bottom

    def _remove_empty_text_elements(
        self, elements: list[LayoutElement]
    ) -> list[LayoutElement]:
        """Drops text-bearing elements that have no actual text.

        Args:
            elements: Elements to check.

        Returns:
            Elements that either carry non-empty text or belong to a
            type that legitimately has none (images, tables).
        """
        kept_elements = []

        for element in elements:
            if element.element_type in _TEXTLESS_TYPES:
                kept_elements.append(element)
                continue

            if element.text.strip():
                kept_elements.append(element)
            else:
                logger.warning(
                    "Dropping element %s on page %d: empty text for type %s",
                    element.id,
                    element.page_number,
                    element.element_type.value,
                )

        return kept_elements

    def _remove_duplicate_ids(
        self, elements: list[LayoutElement]
    ) -> list[LayoutElement]:
        """Drops elements whose id collides with an earlier element's id.

        Args:
            elements: Elements to check, in their current order.

        Returns:
            Elements with unique ids; the first occurrence of any
            colliding id is kept.
        """
        seen_ids: set[str] = set()
        unique_elements = []

        for element in elements:
            if element.id in seen_ids:
                logger.warning(
                    "Dropping element with duplicate id: %s", element.id
                )
                continue

            seen_ids.add(element.id)
            unique_elements.append(element)

        return unique_elements

    def _remove_overlapping_duplicates(
        self, elements: list[LayoutElement]
    ) -> list[LayoutElement]:
        """Drops elements that are near-identical duplicate extractions.

        Two elements are considered the same underlying content if they
        share a type and exact text and their bounding boxes overlap
        heavily. This can happen when a PDF's content stream repeats a
        block (e.g. layered text for a watermark or an OCR artifact).

        Args:
            elements: Elements to check, in their current order.

        Returns:
            Elements with duplicates removed; the first occurrence of
            each duplicate group is kept.
        """
        kept_elements: list[LayoutElement] = []

        for candidate in elements:
            if self._has_duplicate(candidate, kept_elements):
                logger.warning(
                    "Dropping element %s: duplicate extraction of "
                    "existing element",
                    candidate.id,
                )
                continue

            kept_elements.append(candidate)

        return kept_elements

    def _has_duplicate(
        self, candidate: LayoutElement, kept_elements: list[LayoutElement]
    ) -> bool:
        """Checks whether a candidate element duplicates an already-kept one.

        Args:
            candidate: The element being considered.
            kept_elements: Elements already confirmed unique.

        Returns:
            True if any kept element matches the candidate's type and
            text with sufficient bounding-box overlap.
        """
        for kept in kept_elements:
            if kept.element_type != candidate.element_type:
                continue
            if kept.text != candidate.text:
                continue
            if kept.bbox is None or candidate.bbox is None:
                continue

            if self._compute_iou(kept.bbox, candidate.bbox) >= _DUPLICATE_IOU_THRESHOLD:
                return True

        return False

    def _compute_iou(self, first: BoundingBox, second: BoundingBox) -> float:
        """Computes Intersection over Union for two bounding boxes.

        Args:
            first: The first bounding box.
            second: The second bounding box.

        Returns:
            The IoU ratio in [0.0, 1.0]. Zero if the boxes do not
            overlap.
        """
        x_left = max(first.x0, second.x0)
        y_top = max(first.y0, second.y0)
        x_right = min(first.x1, second.x1)
        y_bottom = min(first.y1, second.y1)

        if x_right <= x_left or y_bottom <= y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        union_area = (
            first.width * first.height
            + second.width * second.height
            - intersection_area
        )

        if union_area <= 0:
            return 0.0

        return intersection_area / union_area

    def _remove_dangling_relationships(self, document: LayoutDocument) -> None:
        """Drops relationships that reference elements no longer present.

        Args:
            document: The document being cleaned, with pages already
                validated.
        """
        valid_ids = self._collect_valid_element_ids(document)

        cleaned_relationships = [
            relationship
            for relationship in document.relationships
            if relationship.source_id in valid_ids
            and relationship.target_id in valid_ids
        ]

        removed_count = len(document.relationships) - len(cleaned_relationships)
        if removed_count:
            logger.warning(
                "Removed %d relationship(s) referencing missing elements",
                removed_count,
            )

        document.relationships = cleaned_relationships

    def _remove_dangling_section_references(
        self, document: LayoutDocument
    ) -> None:
        """Repairs sections that reference elements no longer present.

        Args:
            document: The document being cleaned, with pages already
                validated.
        """
        valid_ids = self._collect_valid_element_ids(document)

        for section in document.sections:
            if section.heading is not None and section.heading.id not in valid_ids:
                logger.warning(
                    "Section %s heading %s no longer exists; demoting to "
                    "headless section",
                    section.id,
                    section.heading.id,
                )
                section.heading = None

            original_count = len(section.elements)
            section.elements = [
                element for element in section.elements if element.id in valid_ids
            ]

            removed_count = original_count - len(section.elements)
            if removed_count:
                logger.warning(
                    "Section %s: removed %d reference(s) to missing elements",
                    section.id,
                    removed_count,
                )

    def _collect_valid_element_ids(self, document: LayoutDocument) -> set[str]:
        """Collects the ids of all elements currently present in the document.

        Args:
            document: The document to scan.

        Returns:
            The set of element ids across all pages.
        """
        return {
            element.id for page in document.pages for element in page.elements
        }