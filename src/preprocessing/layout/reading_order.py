"""
OmniBrain - Layout Parsing Engine

Module: Reading Order

Purpose:
    Determine the reading order of already-classified layout elements
    using their coordinates, detected column structure, and alignment.

    This module does not classify elements, build sections, or infer
    relationships. It only orders elements a page already has.
"""

from __future__ import annotations

import logging

from ...models.layout_models import LayoutDocument, LayoutElement, LayoutPage

logger = logging.getLogger(__name__)

# An element is treated as spanning the full page width (e.g. a title,
# section banner, or full-width table) if its width meets or exceeds
# this fraction of the page width. Full-width elements break the
# surrounding content into separate reading bands, which is what lets
# scientific-paper layouts (full-width title/abstract, then two
# columns) and financial reports (narrative text, then a wide table)
# read correctly.
_FULL_WIDTH_RATIO = 0.75

# Minimum width of a vertical whitespace gap, relative to page width,
# required before it is treated as a boundary between two columns
# rather than incidental margin variation.
_MIN_COLUMN_GAP_RATIO = 0.02

# A detected gap only counts as a column boundary if its center falls
# within this horizontal zone of the page. This avoids mistaking
# ordinary left/right page margins for a column split.
_MIDDLE_ZONE_MIN_RATIO = 0.25
_MIDDLE_ZONE_MAX_RATIO = 0.75


class ReadingOrderResolver:
    """Assigns reading order to classified layout elements.

    Elements are grouped into horizontal bands separated by full-width
    elements, and each band is checked for a two-column split. Columns
    are read left-to-right, top-to-bottom within each column, which
    covers single-column text, two-column scientific papers, and
    mixed narrative/table layouts typical of financial reports.
    """

    def assign_reading_order(self, document: LayoutDocument) -> LayoutDocument:
        """Assigns reading order to every element in a document.

        Args:
            document: A `LayoutDocument` with classified elements.

        Returns:
            The same `LayoutDocument` instance. Each element's
            `reading_order` field is set, and each page's `elements`
            list is re-sorted to match reading order.
        """
        logger.info(
            "Assigning reading order for document: %s", document.document_name
        )

        for page in document.pages:
            self._order_page(page)

        return document

    def _order_page(self, page: LayoutPage) -> None:
        """Orders and re-sorts the elements of a single page in place.

        Args:
            page: A `LayoutPage` with classified elements.
        """
        ordered_elements = self._order_elements(page.elements, page.width)

        for index, element in enumerate(ordered_elements):
            element.reading_order = index

        page.elements = ordered_elements

    def _order_elements(
        self, elements: list[LayoutElement], page_width: float
    ) -> list[LayoutElement]:
        """Computes the reading order for a page's elements.

        Args:
            elements: The page's classified elements, in any order.
            page_width: Width of the page.

        Returns:
            Elements in reading order. Elements without a bounding box
            cannot be positioned and are appended at the end, in their
            original relative order.
        """
        positioned = [e for e in elements if e.bbox is not None]
        unpositioned = [e for e in elements if e.bbox is None]

        if unpositioned:
            logger.warning(
                "%d element(s) lack a bounding box and cannot be "
                "positioned in reading order",
                len(unpositioned),
            )

        bands = self._split_into_bands(positioned, page_width)

        ordered: list[LayoutElement] = []
        for band in bands:
            ordered.extend(self._order_band(band, page_width))

        return ordered + unpositioned

    def _split_into_bands(
        self, elements: list[LayoutElement], page_width: float
    ) -> list[list[LayoutElement]]:
        """Splits elements into vertical bands separated by full-width elements.

        Full-width elements (titles, banners, wide tables) each form
        their own single-element band, since they interrupt column
        flow. Non-full-width elements between them are grouped into
        bands to be column-ordered together.

        Args:
            elements: Positioned elements, unsorted.
            page_width: Width of the page.

        Returns:
            An ordered list of bands, top to bottom.
        """
        elements_by_top = sorted(elements, key=lambda e: e.bbox.y0)

        bands: list[list[LayoutElement]] = []
        current_band: list[LayoutElement] = []

        for element in elements_by_top:
            if self._is_full_width(element, page_width):
                if current_band:
                    bands.append(current_band)
                    current_band = []
                bands.append([element])
            else:
                current_band.append(element)

        if current_band:
            bands.append(current_band)

        return bands

    def _is_full_width(self, element: LayoutElement, page_width: float) -> bool:
        """Checks whether an element spans (nearly) the full page width.

        Args:
            element: The element to check.
            page_width: Width of the page.

        Returns:
            True if the element's width meets `_FULL_WIDTH_RATIO` of
            the page width.
        """
        if page_width <= 0:
            return False

        return element.bbox.width >= page_width * _FULL_WIDTH_RATIO

    def _order_band(
        self, band: list[LayoutElement], page_width: float
    ) -> list[LayoutElement]:
        """Orders the elements within a single band.

        Args:
            band: Elements sharing a vertical band, none of them
                full-width.
            page_width: Width of the page.

        Returns:
            Elements in reading order: single reading stream if no
            column split is detected, otherwise left column followed
            by right column, each ordered top to bottom.
        """
        if len(band) <= 1:
            return band

        split_x = self._detect_column_split(band, page_width)
        if split_x is None:
            return sorted(band, key=lambda e: (e.bbox.y0, e.bbox.x0))

        left_column, right_column = self._split_into_columns(band, split_x)
        ordered_left = sorted(left_column, key=lambda e: (e.bbox.y0, e.bbox.x0))
        ordered_right = sorted(right_column, key=lambda e: (e.bbox.y0, e.bbox.x0))

        return ordered_left + ordered_right

    def _detect_column_split(
        self, band: list[LayoutElement], page_width: float
    ) -> float | None:
        """Detects a vertical whitespace gap that separates two columns.

        Merges the horizontal intervals covered by the band's elements
        and looks for a gap between merged intervals that is wide
        enough, and centered enough, to be a genuine column boundary.

        Args:
            band: Elements sharing a vertical band.
            page_width: Width of the page.

        Returns:
            The x-coordinate of the gap's center if a column split is
            detected, otherwise `None` for single-column content.
        """
        merged_intervals = self._merge_horizontal_intervals(band)
        if len(merged_intervals) < 2:
            return None

        gaps = [
            (right[0] - left[1], (left[1] + right[0]) / 2)
            for left, right in zip(merged_intervals, merged_intervals[1:])
        ]
        gap_width, gap_center = max(gaps, key=lambda gap: gap[0])

        meets_minimum_width = gap_width >= page_width * _MIN_COLUMN_GAP_RATIO
        is_centered = (
            page_width * _MIDDLE_ZONE_MIN_RATIO
            <= gap_center
            <= page_width * _MIDDLE_ZONE_MAX_RATIO
        )

        if meets_minimum_width and is_centered:
            return gap_center

        return None

    def _merge_horizontal_intervals(
        self, band: list[LayoutElement]
    ) -> list[tuple[float, float]]:
        """Merges overlapping horizontal extents of a band's elements.

        Args:
            band: Elements sharing a vertical band.

        Returns:
            Non-overlapping (x0, x1) intervals covering the band's
            content, sorted left to right.
        """
        intervals = sorted((e.bbox.x0, e.bbox.x1) for e in band)

        merged: list[list[float]] = [list(intervals[0])]
        for x0, x1 in intervals[1:]:
            if x0 <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], x1)
            else:
                merged.append([x0, x1])

        return [(x0, x1) for x0, x1 in merged]

    def _split_into_columns(
        self, band: list[LayoutElement], split_x: float
    ) -> tuple[list[LayoutElement], list[LayoutElement]]:
        """Splits a band's elements into left and right columns.

        Args:
            band: Elements sharing a vertical band.
            split_x: The x-coordinate of the detected column boundary.

        Returns:
            A tuple of (left_column_elements, right_column_elements),
            assigned by each element's horizontal center.
        """
        left_column = []
        right_column = []

        for element in band:
            center_x = (element.bbox.x0 + element.bbox.x1) / 2
            if center_x < split_x:
                left_column.append(element)
            else:
                right_column.append(element)

        return left_column, right_column