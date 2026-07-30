"""
OmniBrain - Layout Parsing Engine

Module: Layout Extractor

Purpose:
    Extract raw layout information from a PDF document using PyMuPDF.

    This module is responsible for extraction only. It does not classify
    elements, detect headings, determine reading order, build sections,
    infer relationships, or validate the resulting layout. Those concerns
    belong to downstream modules in the layout parsing pipeline.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import fitz  # PyMuPDF

from ...models.layout_models import (
    BoundingBox,
    ElementType,
    FontInfo,
    LayoutDocument,
    LayoutElement,
    LayoutPage,
    PageStatistics,
)

logger = logging.getLogger(__name__)

# PyMuPDF text span flag bitmasks (see PyMuPDF docs on span "flags").
_FLAG_ITALIC = 1 << 1
_FLAG_BOLD = 1 << 4

# PyMuPDF get_text("dict") block type codes.
_BLOCK_TYPE_TEXT = 0
_BLOCK_TYPE_IMAGE = 1


class LayoutExtractor:
    """Extracts raw layout information from a PDF document.

    The extractor reads pages with PyMuPDF and converts each text block,
    image, and detected table into a `LayoutElement`, preserving
    coordinates, typography, and page metadata. No semantic
    interpretation (classification, ordering, hierarchy) is performed
    here.
    """

    def __init__(self, document_name: str) -> None:
        """Initializes the extractor.

        Args:
            document_name: Human-readable name of the document being
                processed. Stored on the resulting `LayoutDocument`.
        """
        self._document_name = document_name

    def extract_document(
        self,
        document: fitz.Document,
        source_path: str = "",
    ) -> LayoutDocument:
        """Extracts raw layout information for an entire PDF document.

        Args:
            pdf_path: Filesystem path to the PDF file.

        Returns:
            A `LayoutDocument` populated with pages and elements, but
            with empty sections and relationships, since those are
            produced by later pipeline stages.

        Raises:
            FileNotFoundError: If the PDF cannot be opened.
        """
        logger.info("Extracting layout for document: %s", self._document_name)

        pages: list[LayoutPage] = []

        for page_index in range(document.page_count):
            page = document[page_index]
            page_number = page_index + 1
            layout_page = self._extract_page(page, page_number)
            pages.append(layout_page)

        total_elements = sum(len(page.elements) for page in pages)
        logger.info(
            "Extraction complete: %d pages, %d elements",
            len(pages),
            total_elements,
        )

        return LayoutDocument(
            document_name=self._document_name,
            pages=pages,
            metadata={"source_path": source_path},
        )

    def _extract_page(self, page: fitz.Page, page_number: int) -> LayoutPage:
        """Extracts all layout elements for a single page.

        Args:
            page: The PyMuPDF page object.
            page_number: One-indexed page number.

        Returns:
            A `LayoutPage` containing extracted elements and statistics.
        """
        page_dict = page.get_text("dict")

        text_elements = self._extract_text_elements(page_dict, page_number)
        image_elements = self._extract_image_elements(page, page_number)
        table_elements = self._extract_table_elements(page, page_number)

        all_elements = text_elements + image_elements + table_elements

        statistics = self._create_page_statistics(
            page_number=page_number,
            text_elements=text_elements,
            image_elements=image_elements,
            table_elements=table_elements,
        )

        return LayoutPage(
            page_number=page_number,
            width=page_dict.get("width", page.rect.width),
            height=page_dict.get("height", page.rect.height),
            elements=all_elements,
            statistics=statistics,
        )

    def _extract_text_elements(
        self, page_dict: dict[str, Any], page_number: int
    ) -> list[LayoutElement]:
        """Extracts text blocks from a page's `get_text("dict")` output.

        Each PyMuPDF text block becomes exactly one `LayoutElement`.

        Args:
            page_dict: Output of `page.get_text("dict")`.
            page_number: One-indexed page number.

        Returns:
            List of extracted text `LayoutElement` objects.
        """
        elements: list[LayoutElement] = []

        for block in page_dict.get("blocks", []):
            if block.get("type") != _BLOCK_TYPE_TEXT:
                continue

            element = self._create_text_element(block, page_number)
            if element is not None:
                elements.append(element)

        return elements

    def _extract_image_elements(
        self, page: fitz.Page, page_number: int
    ) -> list[LayoutElement]:
        """Extracts image elements from a page.

        Args:
            page: The PyMuPDF page object.
            page_number: One-indexed page number.

        Returns:
            List of extracted image `LayoutElement` objects.
        """
        elements: list[LayoutElement] = []

        for block_number, image_info in enumerate(page.get_images(full=True)):
            xref = image_info[0]

            try:
                rects = page.get_image_rects(xref)
            except ValueError:
                logger.warning(
                    "Could not resolve bbox for image xref %d on page %d",
                    xref,
                    page_number,
                )
                continue

            for rect in rects:
                element = self._create_image_element(
                    xref=xref,
                    bbox=rect,
                    page_number=page_number,
                    block_number=block_number,
                )
                elements.append(element)

        return elements

    def _extract_table_elements(
        self, page: fitz.Page, page_number: int
    ) -> list[LayoutElement]:
        """Extracts table elements from a page using PyMuPDF's table finder.

        Args:
            page: The PyMuPDF page object.
            page_number: One-indexed page number.

        Returns:
            List of extracted table `LayoutElement` objects.
        """
        elements: list[LayoutElement] = []

        try:
            found_tables = page.find_tables()
        except Exception:
            logger.exception(
                "Table detection failed on page %d", page_number
            )
            return elements

        for block_number, table in enumerate(found_tables.tables):
            element = self._create_table_element(
                table=table,
                page_number=page_number,
                block_number=block_number,
            )
            elements.append(element)

        return elements

    def _create_text_element(
        self, block: dict[str, Any], page_number: int
    ) -> LayoutElement | None:
        """Builds a `LayoutElement` from a single PyMuPDF text block.

        Args:
            block: A text block dict from `get_text("dict")`.
            page_number: One-indexed page number.

        Returns:
            A populated `LayoutElement`, or `None` if the block contains
            no extractable text.
        """
        lines = block.get("lines", [])
        spans = [span for line in lines for span in line.get("spans", [])]

        text = "".join(span.get("text", "") for span in spans)
        if not text.strip():
            return None

        bbox_values = block.get("bbox", (0.0, 0.0, 0.0, 0.0))
        bbox = BoundingBox(*bbox_values)

        font = self._extract_font_info(spans[0]) if spans else FontInfo()

        return LayoutElement(
            id=self._generate_id(),
            page_number=page_number,
            element_type=ElementType.UNKNOWN,
            text=text,
            bbox=bbox,
            font=font,
            metadata={
                "block_number": block.get("number"),
                "source": "text",
                "line_count": len(lines),
            },
        )

    def _create_image_element(
        self,
        xref: int,
        bbox: fitz.Rect,
        page_number: int,
        block_number: int,
    ) -> LayoutElement:
        """Builds a `LayoutElement` for an image occurrence.

        Args:
            xref: PDF cross-reference number of the image object.
            bbox: Bounding rectangle where the image appears on the page.
            page_number: One-indexed page number.
            block_number: Index of the image among images on the page.

        Returns:
            A populated `LayoutElement` of type `IMAGE`.
        """
        return LayoutElement(
            id=self._generate_id(),
            page_number=page_number,
            element_type=ElementType.IMAGE,
            text="",
            bbox=BoundingBox(bbox.x0, bbox.y0, bbox.x1, bbox.y1),
            font=None,
            metadata={
                "block_number": block_number,
                "source": "image",
                "xref": xref,
            },
        )

    def _create_table_element(
        self,
        table: Any,
        page_number: int,
        block_number: int,
    ) -> LayoutElement:
        """Builds a `LayoutElement` for a detected table.

        Args:
            table: A PyMuPDF `Table` object returned by `find_tables()`.
            page_number: One-indexed page number.
            block_number: Index of the table among tables on the page.

        Returns:
            A populated `LayoutElement` of type `TABLE`. The raw
            extracted cell data is preserved in metadata for downstream
            table-aware chunking; no interpretation happens here.
        """
        bbox = BoundingBox(*table.bbox)

        try:
            extracted_rows = table.extract()
        except Exception:
            logger.exception(
                "Failed to extract table content on page %d", page_number
            )
            extracted_rows = []

        return LayoutElement(
            id=self._generate_id(),
            page_number=page_number,
            element_type=ElementType.TABLE,
            text="",
            bbox=bbox,
            font=None,
            metadata={
                "block_number": block_number,
                "source": "table",
                "row_count": len(extracted_rows),
                "column_count": len(extracted_rows[0]) if extracted_rows else 0,
                "cells": extracted_rows,
            },
        )

    def _extract_font_info(self, span: dict[str, Any]) -> FontInfo:
        """Extracts typography information from a PyMuPDF text span.

        Args:
            span: A span dict from `get_text("dict")`.

        Returns:
            A populated `FontInfo` describing the span's typography.
        """
        flags = span.get("flags", 0)

        return FontInfo(
            name=span.get("font", ""),
            size=span.get("size", 0.0),
            flags=flags,
            color=span.get("color", 0),
            is_bold=bool(flags & _FLAG_BOLD),
            is_italic=bool(flags & _FLAG_ITALIC),
        )

    def _create_page_statistics(
        self,
        page_number: int,
        text_elements: list[LayoutElement],
        image_elements: list[LayoutElement],
        table_elements: list[LayoutElement],
    ) -> PageStatistics:
        """Aggregates raw element counts for a page.

        Args:
            page_number: One-indexed page number.
            text_elements: Extracted text elements on the page.
            image_elements: Extracted image elements on the page.
            table_elements: Extracted table elements on the page.

        Returns:
            A `PageStatistics` summarizing element counts. Deeper
            statistical analysis (font distributions, density, margins)
            is the responsibility of `statistics.py`.
        """
        total = len(text_elements) + len(image_elements) + len(table_elements)

        return PageStatistics(
            page_number=page_number,
            text_elements=len(text_elements),
            image_elements=len(image_elements),
            table_elements=len(table_elements),
            total_elements=total,
        )

    @staticmethod
    def _generate_id() -> str:
        """Generates a globally unique identifier for a layout element.

        Returns:
            A UUID4 hex string.
        """
        return uuid.uuid4().hex