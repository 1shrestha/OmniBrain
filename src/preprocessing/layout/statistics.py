"""
OmniBrain - Layout Parsing Engine

Module: Layout Statistics

Purpose:
    Compute quantitative statistics over already-extracted layout
    elements: font statistics, page density, margins, whitespace,
    indentation, alignment, and spacing.

    This module performs no classification. It only measures and
    aggregates properties of elements produced by `extractor.py`.
"""

from __future__ import annotations

import logging
import statistics as pystats
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ...models.layout_models import (
    DocumentStatistics,
    LayoutDocument,
    LayoutElement,
    LayoutPage,
)

logger = logging.getLogger(__name__)

# Minimum number of samples required before variance-based measures
# (e.g. alignment) are considered meaningful rather than noise.
_MIN_SAMPLES_FOR_VARIANCE = 2


# ==========================================================
# STATISTICS DATA STRUCTURES
# ==========================================================


@dataclass
class Margins:
    """Whitespace margins around content on a page."""

    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0


@dataclass
class FontStatistics:
    """Typography statistics for a set of elements."""

    average_size: float = 0.0
    largest_size: float = 0.0
    smallest_size: float = 0.0
    dominant_font: str = ""
    font_frequency: dict[str, int] = field(default_factory=dict)


@dataclass
class SpacingStatistics:
    """Vertical spacing statistics between elements."""

    average_line_spacing: float = 0.0
    average_element_spacing: float = 0.0


@dataclass
class PageLayoutStatistics:
    """Aggregate layout statistics for a single page."""

    page_number: int
    density: float = 0.0
    whitespace_ratio: float = 0.0
    margins: Margins = field(default_factory=Margins)
    average_indentation: float = 0.0
    dominant_alignment: str = "left"
    font_statistics: FontStatistics = field(default_factory=FontStatistics)
    spacing_statistics: SpacingStatistics = field(
        default_factory=SpacingStatistics
    )


@dataclass
class DocumentLayoutStatistics:
    """Combined per-page and document-level layout statistics."""

    page_statistics: list[PageLayoutStatistics] = field(default_factory=list)
    document_statistics: DocumentStatistics = field(
        default_factory=DocumentStatistics
    )


# ==========================================================
# CALCULATOR
# ==========================================================


class LayoutStatisticsCalculator:
    """Computes layout statistics from extracted elements.

    Consumes the raw output of `LayoutExtractor` and produces
    quantitative measures used by downstream classification and
    reading-order stages. Performs no semantic interpretation.
    """

    def calculate_document_statistics(
        self, document: LayoutDocument
    ) -> DocumentLayoutStatistics:
        """Computes statistics for every page and the document overall.

        Args:
            document: A `LayoutDocument` populated by `LayoutExtractor`.

        Returns:
            A `DocumentLayoutStatistics` containing per-page statistics
            and document-level font statistics.
        """
        logger.info(
            "Calculating layout statistics for document: %s",
            document.document_name,
        )

        page_statistics = [
            self._calculate_page_statistics(page) for page in document.pages
        ]

        document_statistics = self._calculate_document_font_statistics(
            document
        )

        return DocumentLayoutStatistics(
            page_statistics=page_statistics,
            document_statistics=document_statistics,
        )

    def _calculate_page_statistics(self, page: LayoutPage) -> PageLayoutStatistics:
        """Computes all layout statistics for a single page.

        Args:
            page: A `LayoutPage` with extracted elements.

        Returns:
            A `PageLayoutStatistics` for the page.
        """
        text_elements = self._text_elements_with_bbox(page)

        font_statistics = self._calculate_font_statistics(text_elements)
        density = self._calculate_page_density(page)
        margins = self._calculate_margins(page)
        whitespace_ratio = self._calculate_whitespace_ratio(density)
        indentation = self._calculate_indentation(text_elements)
        alignment = self._calculate_alignment(text_elements, page.width)
        spacing = self._calculate_spacing(text_elements)

        return PageLayoutStatistics(
            page_number=page.page_number,
            density=density,
            whitespace_ratio=whitespace_ratio,
            margins=margins,
            average_indentation=indentation,
            dominant_alignment=alignment,
            font_statistics=font_statistics,
            spacing_statistics=spacing,
        )

    def _calculate_font_statistics(
        self, elements: list[LayoutElement]
    ) -> FontStatistics:
        """Computes typography statistics over a set of elements.

        Args:
            elements: Elements with populated `font` data.

        Returns:
            A `FontStatistics` summarizing size range, average size,
            and the most frequently used font name.
        """
        sizes = [e.font.size for e in elements if e.font]
        names = [e.font.name for e in elements if e.font and e.font.name]

        if not sizes:
            return FontStatistics()

        font_frequency = dict(Counter(names))
        dominant_font = self._most_common_key(font_frequency)

        return FontStatistics(
            average_size=sum(sizes) / len(sizes),
            largest_size=max(sizes),
            smallest_size=min(sizes),
            dominant_font=dominant_font,
            font_frequency=font_frequency,
        )

    def _calculate_page_density(self, page: LayoutPage) -> float:
        """Computes the fraction of page area covered by element bboxes.

        Args:
            page: A `LayoutPage` with extracted elements.

        Returns:
            A density ratio in the range [0.0, 1.0]. Overlapping
            elements may cause covered area to exceed the true printed
            area, so the result is clamped at 1.0.
        """
        page_area = page.width * page.height
        if page_area <= 0:
            return 0.0

        covered_area = sum(
            e.bbox.width * e.bbox.height for e in page.elements if e.bbox
        )

        return min(covered_area / page_area, 1.0)

    def _calculate_margins(self, page: LayoutPage) -> Margins:
        """Computes the whitespace margins surrounding page content.

        Args:
            page: A `LayoutPage` with extracted elements.

        Returns:
            A `Margins` describing the gap between the page edges and
            the outermost element bounding boxes. Zero margins on all
            sides if the page has no positioned elements.
        """
        bboxes = [e.bbox for e in page.elements if e.bbox]
        if not bboxes:
            return Margins()

        return Margins(
            top=min(box.y0 for box in bboxes),
            bottom=max(page.height - box.y1 for box in bboxes),
            left=min(box.x0 for box in bboxes),
            right=max(page.width - box.x1 for box in bboxes),
        )

    def _calculate_whitespace_ratio(self, density: float) -> float:
        """Derives the whitespace ratio from page density.

        Args:
            density: Fraction of the page covered by content, in
                [0.0, 1.0].

        Returns:
            The complementary whitespace fraction, in [0.0, 1.0].
        """
        return max(0.0, 1.0 - density)

    def _calculate_indentation(self, elements: list[LayoutElement]) -> float:
        """Computes the average left-edge indentation of elements.

        Args:
            elements: Elements with populated `bbox` data.

        Returns:
            The average x0 coordinate across elements, or 0.0 if none
            are present.
        """
        left_edges = [e.bbox.x0 for e in elements if e.bbox]
        if not left_edges:
            return 0.0

        return sum(left_edges) / len(left_edges)

    def _calculate_alignment(
        self, elements: list[LayoutElement], page_width: float
    ) -> str:
        """Determines the dominant text alignment on a page.

        Compares the variance of left edges, right edges, and
        horizontal centers across elements. The lowest-variance
        dimension indicates the alignment elements were laid out
        against.

        Args:
            elements: Elements with populated `bbox` data.
            page_width: Width of the page, used to detect centering.

        Returns:
            One of "left", "right", "center", or "justified". Defaults
            to "left" when there is not enough data to measure variance.
        """
        bboxes = [e.bbox for e in elements if e.bbox]
        if len(bboxes) < _MIN_SAMPLES_FOR_VARIANCE:
            return "left"

        left_edges = [box.x0 for box in bboxes]
        right_edges = [box.x1 for box in bboxes]
        centers = [(box.x0 + box.x1) / 2 for box in bboxes]

        variances = {
            "left": pystats.pvariance(left_edges),
            "right": pystats.pvariance(right_edges),
            "center": pystats.pvariance(centers),
        }

        left_and_right_aligned = (
            variances["left"] < variances["center"]
            and variances["right"] < variances["center"]
        )
        if left_and_right_aligned:
            return "justified"

        return min(variances, key=variances.get)

    def _calculate_spacing(
        self, elements: list[LayoutElement]
    ) -> SpacingStatistics:
        """Computes vertical spacing statistics between elements.

        Elements are sorted by vertical position and the gaps between
        consecutive elements are measured. Small gaps are treated as
        line spacing within flowing content; larger gaps are treated
        as spacing between distinct elements.

        Args:
            elements: Elements with populated `bbox` data.

        Returns:
            A `SpacingStatistics` with average line and element
            spacing. Zeros when fewer than two elements are present.
        """
        ordered = sorted(
            (e for e in elements if e.bbox), key=lambda e: e.bbox.y0
        )
        if len(ordered) < _MIN_SAMPLES_FOR_VARIANCE:
            return SpacingStatistics()

        gaps = [
            max(0.0, ordered[i].bbox.y0 - ordered[i - 1].bbox.y1)
            for i in range(1, len(ordered))
        ]
        if not gaps:
            return SpacingStatistics()

        median_gap = pystats.median(gaps)
        line_gaps = [gap for gap in gaps if gap <= median_gap] or gaps

        return SpacingStatistics(
            average_line_spacing=sum(line_gaps) / len(line_gaps),
            average_element_spacing=sum(gaps) / len(gaps),
        )

    def _calculate_document_font_statistics(
        self, document: LayoutDocument
    ) -> DocumentStatistics:
        """Computes document-wide font-size statistics.

        Args:
            document: A `LayoutDocument` with extracted pages.

        Returns:
            A `DocumentStatistics` with total counts and font-size
            distribution. `body_font_size` is set to the most frequently
            occurring font size, a common proxy for body text.
        """
        all_elements = [e for page in document.pages for e in page.elements]
        sizes = [e.font.size for e in all_elements if e.font and e.font.size]

        if not sizes:
            return DocumentStatistics(
                total_pages=len(document.pages),
                total_elements=len(all_elements),
            )

        size_frequency = dict(Counter(sizes))
        body_font_size = self._most_common_key(size_frequency)

        return DocumentStatistics(
            total_pages=len(document.pages),
            total_elements=len(all_elements),
            body_font_size=body_font_size,
            average_font_size=sum(sizes) / len(sizes),
            largest_font_size=max(sizes),
            smallest_font_size=min(sizes),
            font_frequency=size_frequency,
        )

    def _text_elements_with_bbox(
        self, page: LayoutPage
    ) -> list[LayoutElement]:
        """Filters a page's elements to those usable for text statistics.

        Args:
            page: A `LayoutPage` with extracted elements.

        Returns:
            Elements that have both text content and a bounding box.
        """
        return [e for e in page.elements if e.text.strip() and e.bbox]

    @staticmethod
    def _most_common_key(frequency: dict) -> Any:
        """Returns the key with the highest frequency count.

        Args:
            frequency: A mapping of value to occurrence count.

        Returns:
            The most frequent key, or an empty string if the mapping
            is empty.
        """
        if not frequency:
            return ""
        return max(frequency, key=frequency.get)