"""
OmniBrain - Layout Parsing Engine

Module: Layout Classifier

Purpose:
    Classify layout elements into semantic types (title, heading,
    subheading, paragraph, header, footer, caption, list, formula,
    code) using the raw elements from `extractor.py` and the
    quantitative statistics from `statistics.py`.

    This module does not determine reading order, build sections, or
    infer relationships between elements. It only assigns
    `ElementType` labels.
"""

from __future__ import annotations

import logging
import re

from ...models.layout_models import (
    ElementType,
    LayoutDocument,
    LayoutElement,
    LayoutPage,
)
from .statistics import DocumentLayoutStatistics, PageLayoutStatistics

logger = logging.getLogger(__name__)

# --- Position thresholds -----------------------------------------------
# Fraction of page height treated as the header / footer zone.
_HEADER_ZONE_RATIO = 0.08
_FOOTER_ZONE_RATIO = 0.08

# --- Font size thresholds -----------------------------------------------
# Multiples of the document's body font size used to distinguish
# titles, headings, and subheadings from ordinary paragraph text.
_TITLE_SIZE_RATIO = 1.5
_HEADING_SIZE_RATIO = 1.25
_SUBHEADING_SIZE_RATIO = 1.1

# --- Text length thresholds ---------------------------------------------
# Titles and headings are short, standalone lines rather than flowing
# paragraphs.
_MAX_HEADING_WORD_COUNT = 20

# --- Pattern-based detection ---------------------------------------------
_BULLET_PREFIXES = ("-", "*", "\u2022", "\u25cf", "\u2013")
_LIST_NUMBERING_PATTERN = re.compile(r"^\s*(\d+[.)]|\(\d+\)|[a-zA-Z][.)])\s+")
_CAPTION_PREFIX_PATTERN = re.compile(
    r"^\s*(figure|fig\.?|table|chart|image|diagram)\s*\d*[:.]?\s*",
    re.IGNORECASE,
)
_FORMULA_SYMBOL_PATTERN = re.compile(
    r"[=∑∫√±≤≥≠∞π∂∇×÷^_{}]|\\frac|\\sum|\\int"
)
_MONOSPACE_FONT_KEYWORDS = (
    "mono",
    "courier",
    "consolas",
    "menlo",
    "code",
)


class ElementClassifier:
    """Assigns semantic `ElementType` labels to layout elements.

    Uses positional, typographic, and textual-pattern heuristics
    derived from the extracted elements and pre-computed statistics.
    Does not reorder, group, or relate elements.
    """

    def classify_document(
        self,
        document: LayoutDocument,
        document_layout_statistics: DocumentLayoutStatistics,
    ) -> LayoutDocument:
        """Classifies every element in a document in place.

        Args:
            document: A `LayoutDocument` populated by `LayoutExtractor`.
            document_layout_statistics: Statistics produced by
                `LayoutStatisticsCalculator.calculate_document_statistics`.

        Returns:
            The same `LayoutDocument` instance, with `element_type` set
            on each element.
        """
        logger.info(
            "Classifying elements for document: %s", document.document_name
        )

        stats_by_page = {
            page_stats.page_number: page_stats
            for page_stats in document_layout_statistics.page_statistics
        }
        body_font_size = (
            document_layout_statistics.document_statistics.body_font_size
        )

        for page in document.pages:
            page_statistics = stats_by_page.get(page.page_number)
            if page_statistics is None:
                logger.warning(
                    "No statistics found for page %d; skipping classification",
                    page.page_number,
                )
                continue

            self._classify_page(page, page_statistics, body_font_size)

        return document

    def _classify_page(
        self,
        page: LayoutPage,
        page_statistics: PageLayoutStatistics,
        body_font_size: float,
    ) -> None:
        """Classifies every element on a single page in place.

        Args:
            page: A `LayoutPage` with extracted elements.
            page_statistics: Statistics for this page.
            body_font_size: Document-wide dominant font size, used as
                the reference point for relative size comparisons.
        """
        for element in page.elements:
            element.element_type = self._classify_element(
                element, page, page_statistics, body_font_size
            )

    def _classify_element(
        self,
        element: LayoutElement,
        page: LayoutPage,
        page_statistics: PageLayoutStatistics,
        body_font_size: float,
    ) -> ElementType:
        """Determines the semantic type of a single element.

        Elements already typed by the extractor (tables, images) are
        passed through unchanged. Text elements are evaluated against
        an ordered set of rules, from most to least specific.

        Args:
            element: The element to classify.
            page: The page the element belongs to.
            page_statistics: Statistics for the element's page.
            body_font_size: Document-wide dominant font size.

        Returns:
            The classified `ElementType`.
        """
        if element.element_type in (ElementType.TABLE, ElementType.IMAGE):
            return element.element_type

        if not element.text.strip():
            return element.element_type

        if self._is_header(element, page):
            return ElementType.HEADER

        if self._is_footer(element, page):
            return ElementType.FOOTER

        if self._is_caption(element):
            return ElementType.CAPTION

        if self._is_code(element):
            return ElementType.CODE

        if self._is_formula(element):
            return ElementType.FORMULA

        if self._is_list(element):
            return ElementType.LIST

        if self._is_title(element, page, body_font_size):
            return ElementType.TITLE

        if self._is_heading(element, body_font_size):
            return ElementType.HEADING

        if self._is_subheading(element, body_font_size):
            return ElementType.SUBTITLE

        return ElementType.PARAGRAPH

    def _is_header(self, element: LayoutElement, page: LayoutPage) -> bool:
        """Checks whether an element sits in the page header zone.

        Args:
            element: The element to check.
            page: The page the element belongs to.

        Returns:
            True if the element's top edge falls within the top
            `_HEADER_ZONE_RATIO` fraction of the page height.
        """
        if element.bbox is None or page.height <= 0:
            return False

        zone_boundary = page.height * _HEADER_ZONE_RATIO
        return element.bbox.y0 <= zone_boundary

    def _is_footer(self, element: LayoutElement, page: LayoutPage) -> bool:
        """Checks whether an element sits in the page footer zone.

        Args:
            element: The element to check.
            page: The page the element belongs to.

        Returns:
            True if the element's bottom edge falls within the bottom
            `_FOOTER_ZONE_RATIO` fraction of the page height.
        """
        if element.bbox is None or page.height <= 0:
            return False

        zone_boundary = page.height * (1.0 - _FOOTER_ZONE_RATIO)
        return element.bbox.y1 >= zone_boundary

    def _is_caption(self, element: LayoutElement) -> bool:
        """Checks whether text matches a figure/table caption pattern.

        Args:
            element: The element to check.

        Returns:
            True if the text starts with a recognized caption prefix,
            e.g. "Figure 1:" or "Table 2.".
        """
        return bool(_CAPTION_PREFIX_PATTERN.match(element.text))

    def _is_code(self, element: LayoutElement) -> bool:
        """Checks whether an element's font indicates source code.

        Args:
            element: The element to check.

        Returns:
            True if the font name contains a known monospace keyword.
        """
        if element.font is None or not element.font.name:
            return False

        font_name = element.font.name.lower()
        return any(keyword in font_name for keyword in _MONOSPACE_FONT_KEYWORDS)

    def _is_formula(self, element: LayoutElement) -> bool:
        """Checks whether text contains a dense concentration of math symbols.

        Args:
            element: The element to check.

        Returns:
            True if mathematical symbols are present and the text is
            short enough to be a standalone formula rather than prose
            that happens to mention a symbol.
        """
        word_count = len(element.text.split())
        if word_count > _MAX_HEADING_WORD_COUNT:
            return False

        return bool(_FORMULA_SYMBOL_PATTERN.search(element.text))

    def _is_list(self, element: LayoutElement) -> bool:
        """Checks whether text begins with a bullet or numbering marker.

        Args:
            element: The element to check.

        Returns:
            True if the text starts with a bullet character or a
            numbered/lettered list marker.
        """
        stripped = element.text.lstrip()
        if stripped.startswith(_BULLET_PREFIXES):
            return True

        return bool(_LIST_NUMBERING_PATTERN.match(stripped))

    def _is_title(
        self, element: LayoutElement, page: LayoutPage, body_font_size: float
    ) -> bool:
        """Checks whether an element is likely the document title.

        Args:
            element: The element to check.
            page: The page the element belongs to.
            body_font_size: Document-wide dominant font size.

        Returns:
            True if the element is on the first page, short, and
            significantly larger than the body font size.
        """
        if page.page_number != 1 or element.font is None:
            return False

        if not self._is_short_line(element):
            return False

        return self._exceeds_size_ratio(
            element.font.size, body_font_size, _TITLE_SIZE_RATIO
        )

    def _is_heading(self, element: LayoutElement, body_font_size: float) -> bool:
        """Checks whether an element is likely a section heading.

        Args:
            element: The element to check.
            body_font_size: Document-wide dominant font size.

        Returns:
            True if the element is a short line with a font
            significantly larger than the body font size, or bold at
            a moderately larger size.
        """
        if element.font is None or not self._is_short_line(element):
            return False

        if self._exceeds_size_ratio(
            element.font.size, body_font_size, _HEADING_SIZE_RATIO
        ):
            return True

        is_moderately_larger = self._exceeds_size_ratio(
            element.font.size, body_font_size, _SUBHEADING_SIZE_RATIO
        )
        return element.font.is_bold and is_moderately_larger

    def _is_subheading(
        self, element: LayoutElement, body_font_size: float
    ) -> bool:
        """Checks whether an element is likely a subheading.

        Args:
            element: The element to check.
            body_font_size: Document-wide dominant font size.

        Returns:
            True if the element is a short line that is either bold or
            slightly larger than the body font size, but not large
            enough to qualify as a heading.
        """
        if element.font is None or not self._is_short_line(element):
            return False

        is_slightly_larger = self._exceeds_size_ratio(
            element.font.size, body_font_size, _SUBHEADING_SIZE_RATIO
        )
        return is_slightly_larger or element.font.is_bold

    def _is_short_line(self, element: LayoutElement) -> bool:
        """Checks whether text is short enough to be a heading-like label.

        Args:
            element: The element to check.

        Returns:
            True if the word count is within `_MAX_HEADING_WORD_COUNT`.
        """
        return len(element.text.split()) <= _MAX_HEADING_WORD_COUNT

    def _exceeds_size_ratio(
        self, font_size: float, body_font_size: float, ratio: float
    ) -> bool:
        """Checks whether a font size exceeds a multiple of the body size.

        Args:
            font_size: The font size being evaluated.
            body_font_size: Document-wide dominant font size.
            ratio: Minimum multiple of `body_font_size` required.

        Returns:
            True if `body_font_size` is unknown (defaults to allowing
            downstream rules to decide) is False; otherwise True only
            when `font_size` meets or exceeds `body_font_size * ratio`.
        """
        if body_font_size <= 0:
            return False

        return font_size >= body_font_size * ratio