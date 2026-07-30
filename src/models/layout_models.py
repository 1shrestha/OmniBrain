"""
OmniBrain - Layout Parsing Engine

Module: Layout Models

Purpose:
    Define the core data models used throughout the layout parsing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ==========================================================
# ENUMS
# ==========================================================


class ElementType(str, Enum):
    """Supported document layout element types."""

    UNKNOWN = "unknown"

    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TITLE = "title"
    SUBTITLE = "subtitle"

    LIST = "list"
    LIST_ITEM = "list_item"

    TABLE = "table"
    FIGURE = "figure"
    IMAGE = "image"

    CAPTION = "caption"

    HEADER = "header"
    FOOTER = "footer"

    PAGE_NUMBER = "page_number"

    FORMULA = "formula"
    CODE = "code"


class ReadingDirection(str, Enum):
    """Supported document reading directions."""

    LEFT_TO_RIGHT = "left_to_right"
    RIGHT_TO_LEFT = "right_to_left"
    TOP_TO_BOTTOM = "top_to_bottom"


class RelationshipType(str, Enum):
    """Relationship between layout elements."""

    PARENT = "parent"
    CHILD = "child"

    NEXT = "next"
    PREVIOUS = "previous"

    CAPTION_OF = "caption_of"

    PART_OF = "part_of"


# ==========================================================
# BASIC DATA STRUCTURES
# ==========================================================


@dataclass
class BoundingBox:
    """Bounding box coordinates."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass
class FontInfo:
    """Typography information."""

    name: str = ""
    size: float = 0.0
    flags: int = 0
    color: int = 0
    is_bold: bool = False
    is_italic: bool = False


# ==========================================================
# LAYOUT ELEMENTS
# ==========================================================


@dataclass
class LayoutElement:
    """Single document layout element."""

    id: str

    page_number: int

    element_type: ElementType = ElementType.UNKNOWN

    text: str = ""

    bbox: BoundingBox | None = None

    font: FontInfo | None = None

    confidence: float = 1.0

    metadata: dict[str, Any] = field(default_factory=dict)

    reading_order: int = -1

    parent_id: str | None = None

    children: list[str] = field(default_factory=list)


# ==========================================================
# PAGE STATISTICS
# ==========================================================

@dataclass
class PageStatistics:
    """Statistics collected during layout extraction for a single page."""

    page_number: int

    text_elements: int = 0

    image_elements: int = 0

    table_elements: int = 0

    total_elements: int = 0


@dataclass
class LayoutPage:
    """Represents a single document page."""

    page_number: int

    width: float

    height: float

    elements: list[LayoutElement] = field(default_factory=list)

    statistics: PageStatistics = field(
    default_factory=lambda: PageStatistics(page_number=0)
    )


# ==========================================================
# RELATIONSHIPS
# ==========================================================


@dataclass
class ElementRelationship:
    """Relationship between two layout elements."""

    source_id: str

    target_id: str

    relationship: RelationshipType


# ==========================================================
# DOCUMENT SECTIONS
# ==========================================================


@dataclass
class LayoutSection:
    """Logical document section."""

    id: str

    title: str

    heading: LayoutElement | None = None

    elements: list[LayoutElement] = field(default_factory=list)

    level: int = 1


# ==========================================================
# DOCUMENT STATISTICS
# ==========================================================


@dataclass
class DocumentStatistics:
    """Typography and layout statistics."""

    total_pages: int = 0

    total_elements: int = 0

    body_font_size: float = 0.0

    average_font_size: float = 0.0

    largest_font_size: float = 0.0

    smallest_font_size: float = 0.0

    font_frequency: dict[float, int] = field(default_factory=dict)


# ==========================================================
# FINAL DOCUMENT
# ==========================================================


@dataclass
class LayoutDocument:
    """Complete parsed layout document."""

    document_name: str

    pages: list[LayoutPage] = field(default_factory=list)

    sections: list[LayoutSection] = field(default_factory=list)

    relationships: list[ElementRelationship] = field(default_factory=list)

    statistics: DocumentStatistics = field(default_factory=DocumentStatistics)

    metadata: dict[str, Any] = field(default_factory=dict)