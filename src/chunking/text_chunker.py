"""
OmniBrain

Module: Text Chunker

Purpose:
    Split cleaned text into semantic chunks for
    embedding and retrieval.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

from configs.settings import Settings


class TextChunker:
    """
    Split cleaned text into overlapping semantic chunks.
    """

    def __init__(
        self,
        pdf_path: Path,
    ) -> None:

        self.pdf_path = Path(pdf_path)

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=Settings.CHUNK_SIZE,
            chunk_overlap=Settings.CHUNK_OVERLAP,
            separators=Settings.CHUNK_SEPARATORS,
            length_function=len,
            is_separator_regex=False,
        )

    def chunk(
        self,
        text_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate semantic chunks from extracted text.
        """

        chunks = []

        relative_source = self.pdf_path.relative_to(
            Settings.PROJECT_ROOT
        )

        for page in text_data["pages"]:

            page_number = page["page"]

            text = page["text"].strip()

            extraction_method = page[
                "extraction_method"
            ]

            if not text:
                continue

            page_chunks = self.splitter.split_text(
                text
            )

            for index, chunk in enumerate(
                page_chunks,
                start=1,
            ):

                chunk = chunk.strip()

                if not chunk:
                    continue

                chunk_id = (
                    f"{metadata['document_id'][:8]}"
                    f"_p{page_number:03}"
                    f"_c{index:03}"
                )

                chunks.append(
                    {
                        "chunk_id": chunk_id,

                        "document_id": metadata[
                            "document_id"
                        ],

                        "document": self.pdf_path.name,

                        "page_number": page_number,

                        "chunk_index": index,

                        "source": str(
                            relative_source
                        ),

                        "text": chunk,

                        "char_count": len(
                            chunk
                        ),

                        "word_count": len(
                            chunk.split()
                        ),

                        "chunk_size": Settings.CHUNK_SIZE,

                        "chunk_overlap": Settings.CHUNK_OVERLAP,

                        "extraction_method": extraction_method,
                    }
                )

        return {

            "document_id": metadata[
                "document_id"
            ],

            "document": self.pdf_path.name,

            "chunk_count": len(chunks),

            "chunks": chunks,
        }

    def save(
        self,
        chunk_data: dict[str, Any],
    ) -> Path:
        """
        Save chunks as JSON.
        """

        output_path = (
            Settings.CHUNK_OUTPUT_DIR
            / f"{self.pdf_path.stem}_chunks.json"
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                chunk_data,
                file,
                indent=4,
                ensure_ascii=False,
            )

        return output_path