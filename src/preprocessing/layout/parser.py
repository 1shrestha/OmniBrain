"""
OmniBrain - Layout Parsing Engine

Module: Parser

Purpose:
    Master orchestrator for the layout parsing pipeline. Wires the
    extractor, statistics calculator, classifier, reading order
    resolver, relationship detector, section builder, and validator
    together in sequence and returns the finished `LayoutDocument`.

    Pipeline:
        Extractor
          -> Statistics
          -> Classifier
          -> Reading Order
          -> Relationships
          -> Section Builder
          -> Validator

    This module does not itself extract, classify, order, relate,
    section, or validate anything — it only sequences the modules that
    do.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Callable, TypeVar

from ...models.layout_models import LayoutDocument
from .classifier import ElementClassifier
from .extractor import LayoutExtractor
from .reading_order import ReadingOrderResolver
from .relationships import RelationshipDetector
from .section_builder import SectionBuilder
from .statistics import DocumentLayoutStatistics, LayoutStatisticsCalculator
from .validator import LayoutValidator

logger = logging.getLogger(__name__)

_StageResult = TypeVar("_StageResult")


class LayoutParsingError(Exception):
    """Raised when a stage of the layout parsing pipeline fails."""


class LayoutParser:
    """Master orchestrator for the layout parsing pipeline.

    Constructs (or accepts, for dependency injection and testing) one
    instance of each pipeline stage and runs a PDF through all of them
    in order, producing a fully extracted, classified, ordered,
    related, sectioned, and validated `LayoutDocument`.
    """

    def __init__(
        self,
        statistics_calculator: LayoutStatisticsCalculator | None = None,
        classifier: ElementClassifier | None = None,
        reading_order_resolver: ReadingOrderResolver | None = None,
        relationship_detector: RelationshipDetector | None = None,
        section_builder: SectionBuilder | None = None,
        validator: LayoutValidator | None = None,
    ) -> None:
        """Initializes the parser with its pipeline stages.

        Args:
            statistics_calculator: Statistics stage. Defaults to a new
                `LayoutStatisticsCalculator`.
            classifier: Classification stage. Defaults to a new
                `ElementClassifier`.
            reading_order_resolver: Reading order stage. Defaults to a
                new `ReadingOrderResolver`.
            relationship_detector: Relationship detection stage.
                Defaults to a new `RelationshipDetector`.
            section_builder: Section building stage. Defaults to a new
                `SectionBuilder`.
            validator: Validation stage. Defaults to a new
                `LayoutValidator`.
        """
        self._statistics_calculator = (
            statistics_calculator or LayoutStatisticsCalculator()
        )
        self._classifier = classifier or ElementClassifier()
        self._reading_order_resolver = (
            reading_order_resolver or ReadingOrderResolver()
        )
        self._relationship_detector = (
            relationship_detector or RelationshipDetector()
        )
        self._section_builder = section_builder or SectionBuilder()
        self._validator = validator or LayoutValidator()

    def parse_document(
        self,
        document,
        pdf_path: str,
        document_name: str | None = None,
    ) -> LayoutDocument:
        """Runs the full layout parsing pipeline over a PDF.

        Args:
            pdf_path: Filesystem path to the PDF file.
            document_name: Optional human-readable document name. If
                omitted, it is derived from the PDF's filename.

        Returns:
            A fully processed `LayoutDocument`.

        Raises:
            LayoutParsingError: If any pipeline stage fails. The
                original exception is chained as the cause.
        """
        resolved_name = document_name or self._derive_document_name(pdf_path)
        logger.info(
            "Starting layout parsing pipeline for '%s' (%s)",
            resolved_name,
            pdf_path,
        )

        document = self._execute_stage(
            "extraction", lambda: self._extract(document, pdf_path, resolved_name)
        )
        document_statistics = self._execute_stage(
            "statistics",
            lambda: self._statistics_calculator.calculate_document_statistics(
                document
            ),
        )
        document = self._execute_stage(
            "classification",
            lambda: self._classifier.classify_document(
                document, document_statistics
            ),
        )
        document = self._execute_stage(
            "reading_order",
            lambda: self._reading_order_resolver.assign_reading_order(document),
        )
        document = self._execute_stage(
            "relationships",
            lambda: self._relationship_detector.detect_relationships(document),
        )
        document = self._execute_stage(
            "section_building",
            lambda: self._section_builder.build_sections(document),
        )
        document = self._execute_stage(
            "validation", lambda: self._validator.validate_document(document)
        )

        logger.info(
            "Completed layout parsing pipeline for '%s'", resolved_name
        )

        return document

    def _extract(
        self,
        document,
        pdf_path: str,
        document_name: str,
    ) -> LayoutDocument:
        """Runs the extraction stage.

        A new `LayoutExtractor` is created per call, since it is scoped
        to a single document name, unlike the other pipeline stages
        which are stateless and reused across documents.

        Args:
            pdf_path: Filesystem path to the PDF file.
            document_name: Resolved human-readable document name.

        Returns:
            A `LayoutDocument` with raw extracted pages and elements.
        """
        extractor = LayoutExtractor(document_name)
        return extractor.extract_document(document=document, source_path=pdf_path)

    def _execute_stage(
        self, stage_name: str, stage_callable: Callable[[], _StageResult]
    ) -> _StageResult:
        """Runs a single pipeline stage with timing and error handling.

        Args:
            stage_name: Human-readable name of the stage, used in logs
                and error messages.
            stage_callable: A zero-argument callable that performs the
                stage's work and returns its result.

        Returns:
            Whatever `stage_callable` returns.

        Raises:
            LayoutParsingError: If `stage_callable` raises. The
                original exception is chained as the cause.
        """
        start_time = time.perf_counter()

        try:
            result = stage_callable()
        except Exception as exc:
            logger.exception("Layout parsing stage '%s' failed", stage_name)
            raise LayoutParsingError(
                f"Stage '{stage_name}' failed: {exc}"
            ) from exc

        elapsed_seconds = time.perf_counter() - start_time
        logger.info(
            "Stage '%s' completed in %.3fs", stage_name, elapsed_seconds
        )

        return result

    def _derive_document_name(self, pdf_path: str) -> str:
        """Derives a document name from a PDF's filename.

        Args:
            pdf_path: Filesystem path to the PDF file.

        Returns:
            The filename without its directory or extension.
        """
        base_name = os.path.basename(pdf_path)
        return os.path.splitext(base_name)[0]