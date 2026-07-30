"""
OmniBrain - PDF Ingestion Engine

Module: OCR Extractor

Purpose:
    OCR service used as a fallback for scanned PDF pages.
"""

from __future__ import annotations

from typing import Sequence

import fitz
import torch
import easyocr
from PIL import Image

from configs.settings import Settings


class OCRExtractor:
    """
    OCR service for scanned PDF pages.

    This class processes one PDF page at a time.
    The TextExtractor decides when OCR is required.
    """

    def __init__(
        self,
        languages: Sequence[str] | None = None,
        gpu: bool | None = None,
    ) -> None:
        """
        Initialize the OCR engine.

        Args:
            languages:
                OCR language list. Defaults to Settings.OCR_LANGUAGES.

            gpu:
                Optional GPU override.
                If None, Settings.OCR_GPU is used.
        """

        self.languages = list(
            languages or Settings.OCR_LANGUAGES
        )

        self.use_gpu = (
            Settings.OCR_GPU
            if gpu is None
            else gpu
        )

        self.reader = easyocr.Reader(
            self.languages,
            gpu=self.use_gpu,
        )

    def _page_to_image(
        self,
        page: fitz.Page,
    ) -> Image.Image:
        """
        Convert a PDF page into a high-resolution RGB image.
        """

        matrix = fitz.Matrix(
            Settings.OCR_DPI,
            Settings.OCR_DPI,
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        return Image.frombytes(
            "RGB",
            (
                pixmap.width,
                pixmap.height,
            ),
            pixmap.samples,
        )

    @torch.inference_mode()
    def extract_page(
        self,
        page: fitz.Page,
    ) -> str:
        """
        Perform OCR on a single PDF page.

        Returns:
            Extracted text.
        """

        image = self._page_to_image(page)

        result = self.reader.readtext(
            image,
            detail=0,
            paragraph=True,
        )

        if not result:
            return ""

        return "\n".join(
            str(line).strip()
            for line in result
            if str(line).strip()
        )