"""
Module: Metadata Extractor

Purpose:
    Extract metadata from a PDF document and store
    it as a structured JSON file.

Responsibilities:
    - Extract document metadata
    - Generate document identifier
    - Format PDF date fields
    - Calculate file size
    - Save metadata to JSON
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz

from configs.settings import Settings


class MetadataExtractor:
    """
    Extract metadata from a PDF document.
    """

    def __init__(
        self,
        pdf_path: Path,
        document: fitz.Document,
    ) -> None:

        self.pdf_path = Path(pdf_path)
        self.document = document

    @staticmethod
    def _format_pdf_date(
        date_string: str | None,
    ) -> str | None:
        """
        Convert PDF date into a readable format.
        """

        if not date_string:
            return None

        try:

            cleaned = date_string.replace(
                "D:",
                "",
            )[:14]

            return datetime.strptime(
                cleaned,
                "%Y%m%d%H%M%S",
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        except Exception:

            return date_string

    def _generate_document_id(self) -> str:
        """
        Generate a unique document identifier based
        on the PDF file contents.
        """

        sha256 = hashlib.sha256()

        with open(
            self.pdf_path,
            "rb",
        ) as file:

            while True:

                data = file.read(8192)

                if not data:
                    break

                sha256.update(data)

        return sha256.hexdigest()

    def extract(self) -> dict[str, Any]:
        """
        Extract metadata from the PDF.
        """

        raw = self.document.metadata

        relative_path = self.pdf_path.relative_to(
            Settings.PROJECT_ROOT
        )

        metadata = {

            "document_id": self._generate_document_id(),

            "filename": self.pdf_path.name,

            "extension": self.pdf_path.suffix.lower(),

            "file_path": str(
                relative_path
            ),

            "file_size_mb": round(
                self.pdf_path.stat().st_size /
                (1024 * 1024),
                2,
            ),

            "pages": self.document.page_count,

            "title": raw.get("title"),

            "author": raw.get("author"),

            "subject": raw.get("subject"),

            "keywords": raw.get("keywords"),

            "creator": raw.get("creator"),

            "producer": raw.get("producer"),

            "creation_date": self._format_pdf_date(
                raw.get("creationDate")
            ),

            "modification_date": self._format_pdf_date(
                raw.get("modDate")
            ),

            "encrypted": self.document.needs_pass,

            "pdf_version": raw.get(
                "format",
                "Unknown",
            ),

            "processed_at": datetime.now().isoformat(),
        }

        return metadata

    def save(
        self,
        metadata: dict[str, Any],
    ) -> Path:
        """
        Save metadata as JSON.
        """

        output_path = (
            Settings.METADATA_DIR
            / f"{self.pdf_path.stem}.json"
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as json_file:

            json.dump(
                metadata,
                json_file,
                indent=4,
                ensure_ascii=False,
            )

        return output_path