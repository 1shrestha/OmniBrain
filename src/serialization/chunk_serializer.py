"""
OmniBrain - Chunk Serializer

Serialize ChunkCollection into the legacy *_chunks.json format
expected by the current EmbeddingGenerator.
"""

from __future__ import annotations

import json
from pathlib import Path

from configs.settings import Settings
from src.models.chunk_models import ChunkCollection


class ChunkSerializer:

    def __init__(self):
        Settings.CHUNK_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def save(self, collection: ChunkCollection) -> Path:

        chunks = []

        for chunk in collection.chunks:
            chunks.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document": collection.document_name,
                    "page_number": chunk.metadata.page_start,
                    "chunk_index": chunk.metadata.chunk_index,
                    "text": chunk.text,
                    "chunk_type": chunk.chunk_type.value,
                    "section_title": chunk.metadata.section_title,
                    "section_level": chunk.metadata.section_level,
                    "page_start": chunk.metadata.page_start,
                    "page_end": chunk.metadata.page_end,
                    "reading_order_start": chunk.metadata.reading_order_start,
                    "reading_order_end": chunk.metadata.reading_order_end,
                    "element_ids": chunk.metadata.element_ids,
                    "element_types": chunk.metadata.element_types,
                    "statistics": {
                        "char_count": chunk.statistics.char_count,
                        "word_count": chunk.statistics.word_count,
                        "element_count": chunk.statistics.element_count,
                        "has_table": chunk.statistics.has_table,
                        "has_image": chunk.statistics.has_image,
                        "has_code": chunk.statistics.has_code,
                        "has_formula": chunk.statistics.has_formula,
                    },
                }
            )

        output = {
            "document_id": collection.document_id,
            "document": collection.document_name,
            "chunk_count": collection.chunk_count,
            "chunks": chunks,
        }

        output_file = (
            Settings.CHUNK_OUTPUT_DIR /
            f"{collection.document_name}_chunks.json"
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, ensure_ascii=False)

        return output_file
