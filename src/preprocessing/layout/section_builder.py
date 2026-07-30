"""
OmniBrain - Layout Parsing Engine

Module: Section Builder

Purpose:
    Build the document's logical hierarchy — Document -> Sections ->
    Subsections -> Paragraphs — from already-classified,
    already-ordered elements and the relationships detected between
    them.

    This module does not classify elements, determine reading order,
    or detect relationships itself. It consumes those outputs and
    organizes elements into `LayoutSection` groups.

Hierarchy representation convention:
    `LayoutSection` has no parent-section reference. Hierarchy is
    represented the way a table of contents is: a flat, ordered list of
    sections (`LayoutDocument.sections`), each carrying a `level`
    (1 = section, from a `TITLE`; 2 = section, from a `HEADING`;
    3 = subsection, from a `SUBTITLE`). Nesting is inferred from level
    plus sequential position, not from an explicit parent pointer.
    Content elements (paragraphs, lists, tables, images, code,
    formulas) live directly on the section that owns them; they are
    never sections themselves.
"""

from __future__ import annotations

import logging
import uuid

from ...models.layout_models import (
    ElementRelationship,
    ElementType,
    LayoutDocument,
    LayoutElement,
    LayoutSection,
    RelationshipType,
)

logger = logging.getLogger(__name__)

# Maps heading-like element types to their section nesting level.
_LEVEL_BY_TYPE = {
    ElementType.TITLE: 1,
    ElementType.HEADING: 2,
    ElementType.SUBTITLE: 3,
}

# Level assigned to content that appears before any heading-like
# element (e.g. running text before the first section). Treated as
# top-level, matching a document title's level.
_PREAMBLE_LEVEL = 1


class SectionBuilder:
    """Builds the document hierarchy from relationships and reading order.

    Walks elements in reading order, opening a new `LayoutSection`
    whenever a heading-like element is encountered, and assigning each
    content element to the section that owns it according to the
    `PARENT` relationships produced by `RelationshipDetector`.
    """

    def build_sections(self, document: LayoutDocument) -> LayoutDocument:
        """Builds the section hierarchy for a document.

        Args:
            document: A `LayoutDocument` with classified elements in
                reading order and relationships already detected.

        Returns:
            The same `LayoutDocument` instance, with `sections`
            populated.
        """
        logger.info(
            "Building sections for document: %s", document.document_name
        )

        ordered_elements = self._flatten_in_reading_order(document)
        ownership_map = self._build_heading_ownership_map(
            document.relationships
        )

        sections: list[LayoutSection] = []
        section_by_heading_id: dict[str, LayoutSection] = {}
        preamble_section: LayoutSection | None = None
        current_section: LayoutSection | None = None

        for element in ordered_elements:
            if element.element_type in _LEVEL_BY_TYPE:
                current_section = self._create_section(element)
                sections.append(current_section)
                section_by_heading_id[element.id] = current_section
                continue

            target_section = self._resolve_target_section(
                element, ownership_map, section_by_heading_id, current_section
            )

            if target_section is None:
                if preamble_section is None:
                    preamble_section = self._create_preamble_section()
                    sections.insert(0, preamble_section)
                target_section = preamble_section

            target_section.elements.append(element)

        document.sections = sections

        logger.info("Built %d section(s)", len(sections))

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

    def _build_heading_ownership_map(
        self, relationships: list[ElementRelationship]
    ) -> dict[str, str]:
        """Builds a lookup from content element id to its owning heading id.

        Derived from the `PARENT` relationships produced by
        `RelationshipDetector`, where the source is a heading-like
        element and the target is the content it owns.

        Args:
            relationships: All relationships detected for the document.

        Returns:
            A mapping of content element id to heading element id. If
            more than one `PARENT` relationship targets the same
            content element, the first one encountered wins and the
            rest are logged and discarded.
        """
        ownership_map: dict[str, str] = {}

        for relationship in relationships:
            if relationship.relationship != RelationshipType.PARENT:
                continue

            if relationship.target_id in ownership_map:
                logger.warning(
                    "Element %s already has an owning heading; ignoring "
                    "additional PARENT relationship from %s",
                    relationship.target_id,
                    relationship.source_id,
                )
                continue

            ownership_map[relationship.target_id] = relationship.source_id

        return ownership_map

    def _resolve_target_section(
        self,
        element: LayoutElement,
        ownership_map: dict[str, str],
        section_by_heading_id: dict[str, LayoutSection],
        current_section: LayoutSection | None,
    ) -> LayoutSection | None:
        """Determines which section a content element belongs to.

        Prefers the section whose heading was explicitly linked to this
        element via a `PARENT` relationship. Falls back to the most
        recently opened section if no explicit relationship exists,
        which keeps ordinary flowing content attached to its section
        even when relationship detection missed an edge.

        Args:
            element: The content element being placed.
            ownership_map: Content id to owning heading id, from
                `_build_heading_ownership_map`.
            section_by_heading_id: Heading id to the `LayoutSection` it
                opened.
            current_section: The most recently opened section, if any.

        Returns:
            The `LayoutSection` this element belongs to, or `None` if
            no heading has been encountered yet.
        """
        owning_heading_id = ownership_map.get(element.id)
        if owning_heading_id is not None:
            owning_section = section_by_heading_id.get(owning_heading_id)
            if owning_section is not None:
                return owning_section

        return current_section

    def _create_section(self, heading: LayoutElement) -> LayoutSection:
        """Creates a new section opened by a heading-like element.

        Args:
            heading: The `TITLE`, `HEADING`, or `SUBTITLE` element
                opening this section.

        Returns:
            A new, empty `LayoutSection` at the level matching the
            heading's type.
        """
        level = _LEVEL_BY_TYPE.get(heading.element_type, _PREAMBLE_LEVEL)

        return LayoutSection(
            id=self._generate_id(),
            title=heading.text.strip(),
            heading=heading,
            elements=[],
            level=level,
        )

    def _create_preamble_section(self) -> LayoutSection:
        """Creates the implicit section holding content before any heading.

        Some documents contain running text before the first heading
        (e.g. an abstract or a byline). That content must still be
        preserved rather than dropped, so it is collected into a
        heading-less section placed first.

        Returns:
            A new, empty `LayoutSection` with no heading.
        """
        return LayoutSection(
            id=self._generate_id(),
            title="",
            heading=None,
            elements=[],
            level=_PREAMBLE_LEVEL,
        )

    @staticmethod
    def _generate_id() -> str:
        """Generates a globally unique identifier for a section.

        Returns:
            A UUID4 hex string.
        """
        return uuid.uuid4().hex