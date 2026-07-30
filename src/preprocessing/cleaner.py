"""
OmniBrain

Module: Text Cleaner

Purpose:
    Clean extracted PDF text while preserving
    document structure and semantic meaning.
"""

from __future__ import annotations

import re
import unicodedata


class TextCleaner:
    """
    Clean extracted PDF text while preserving
    semantic structure.
    """

    @staticmethod
    def clean(text: str) -> str:
        """
        Clean extracted text.

        Parameters
        ----------
        text : str
            Raw extracted text.

        Returns
        -------
        str
            Cleaned text.
        """

        if not text:
            return ""

        # Normalize Unicode characters

        text = unicodedata.normalize(
            "NFKC",
            text,
        )

        # Normalize line endings

        text = text.replace(
            "\r\n",
            "\n",
        )

        text = text.replace(
            "\r",
            "\n",
        )

        # Replace non-breaking spaces

        text = text.replace(
            "\u00A0",
            " ",
        )

        # Remove soft hyphens

        text = text.replace(
            "\u00AD",
            "",
        )

        # Replace tabs

        text = text.replace(
            "\t",
            " ",
        )

        # Remove trailing spaces from each line

        lines = [
            line.rstrip()
            for line in text.split("\n")
        ]

        text = "\n".join(lines)

        # Collapse multiple spaces

        text = re.sub(
            r"[ ]{2,}",
            " ",
            text,
        )

        # Collapse excessive blank lines
        # Preserve paragraph separation

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        # Remove spaces before punctuation

        text = re.sub(
            r"\s+([.,;:!?])",
            r"\1",
            text,
        )

        # Remove leading and trailing whitespace

        text = text.strip()

        return text