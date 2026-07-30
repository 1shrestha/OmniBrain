"""
OmniBrain - PDF Ingestion Engine

Module: Text Extractor

Purpose:
    Extract searchable text from PDF documents using
    PyMuPDF with automatic OCR fallback.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from configs.settings import Settings
from src.ingestion.ocr import OCRExtractor


class TextExtractor:
    """
    Extract searchable text from a PDF.

    Workflow:
        1. Try native text extraction.
        2. If insufficient text is found, perform OCR.
        3. Save a unified text output.
    """

    def __init__(
        self,
        pdf_path: Path,
        document: fitz.Document,
    ) -> None:

        self.pdf_path = Path(pdf_path)
        self.document = document

        # OCR engine is initialized only when required.
        self.ocr: OCRExtractor | None = None

    def extract(self) -> dict[str, Any]:
        """
        Extract text from every page in the PDF.

        Returns:
            Dictionary containing extracted text and metadata.
        """

        pages: list[dict[str, Any]] = []

        total_characters = 0
        empty_pages: list[int] = []

        ocr_pages = 0
        ocr_page_numbers: list[int] = []

        for page_number, page in enumerate(
            self.document,
            start=1,
        ):

            text = page.get_text("text").strip()

            extraction_method = "text"

            if len(text) < Settings.OCR_THRESHOLD:

                if self.ocr is None:

                    print("[INFO] Initializing OCR Engine...")

                    self.ocr = OCRExtractor()

                try:

                    ocr_text = self.ocr.extract_page(page)

                    if ocr_text:

                        text = ocr_text

                        extraction_method = "ocr"

                        ocr_pages += 1
                        ocr_page_numbers.append(page_number)

                except Exception as error:

                    print(
                        f"[WARNING] OCR failed on page "
                        f"{page_number}: {error}"
                    )

            if not text:

                empty_pages.append(page_number)

            total_characters += len(text)

            pages.append(
                {
                    "page": page_number,
                    "text": text,
                    "extraction_method": extraction_method,
                }
            )

        return {
            "pages": pages,
            "page_count": len(pages),
            "empty_pages": empty_pages,
            "ocr_pages": ocr_pages,
            "ocr_page_numbers": ocr_page_numbers,
            "total_characters": total_characters,
        }

    def save(
        self,
        extraction_result: dict[str, Any],
    ) -> Path:
        """
        Save extracted text to disk.

        Returns:
            Path to the saved text file.
        """

        Settings.TEXT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file = (
            Settings.TEXT_DIR /
            f"{self.pdf_path.stem}.txt"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as file:

            for page in extraction_result["pages"]:

                file.write("=" * 80 + "\n")
                file.write(f"PAGE {page['page']}\n")
                file.write("=" * 80 + "\n\n")

                file.write(page["text"])

                file.write("\n\n")

        return output_file