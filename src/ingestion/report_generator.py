"""
OmniBrain - PDF Ingestion Engine

Module: Report Generator

Purpose:
    Generate a structured ingestion report for every PDF.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from configs.settings import Settings


class ReportGenerator:
    """
    Generate a structured PDF ingestion report.
    """

    def __init__(
        self,
        pdf_path: Path,
    ) -> None:

        self.pdf_path = Path(pdf_path)

    def generate(
        self,
        metadata: dict[str, Any],
        text: dict[str, Any],
        chunks: dict[str, Any],
        images: dict[str, Any],
        tables: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate ingestion report.
        """

        report = {

            "document_id": metadata["document_id"],

            "document": self.pdf_path.name,

            "generated_at": datetime.now().isoformat(),

            "status": "SUCCESS",

            "pipeline_version": "2.0",

            "metadata": metadata,

            "summary": {

                "pages": metadata["pages"],

                "characters": text["total_characters"],

                "empty_pages": len(
                    text["empty_pages"]
                ),

                "ocr_pages": text["ocr_pages"],

                "chunks": chunks["chunk_count"],

                "images": images["unique_images"],

                "tables": tables["count"],

            },

            "chunk_statistics": {

                "original_chunk_count":
                    chunks["statistics"]["original_chunk_count"],

                "validated_chunk_count":
                    chunks["statistics"]["validated_chunk_count"],

                "largest_chunk":
                    chunks["statistics"]["largest_chunk"],

                "smallest_chunk":
                    chunks["statistics"]["smallest_chunk"],

                "average_chunk_size":
                    chunks["statistics"]["average_chunk_size"],

                "average_word_count":
                    chunks["statistics"]["average_word_count"],

                "total_characters":
                    chunks["statistics"]["total_characters"],

                "total_words":
                    chunks["statistics"]["total_words"],

                "merged_chunks":
                    chunks["statistics"]["merged_chunks"],

                "removed_empty":
                    chunks["statistics"]["removed_empty"],

                "removed_duplicates":
                    chunks["statistics"]["removed_duplicates"],

            },

            "image_statistics": {

                "total_images":
                    images["count"],

                "unique_images":
                    images["unique_images"],

            },

            "table_statistics": {

                "total_tables":
                    tables["count"],

            },

            "embedding_configuration": {

                "model":
                    Settings.EMBEDDING_MODEL,

                "vector_dimension":
                    Settings.VECTOR_DIMENSION,

                "normalized":
                    Settings.NORMALIZE_EMBEDDINGS,

                "device":
                    Settings.EMBEDDING_DEVICE,

            },

            "vector_database": {

                "provider": "Qdrant",

                "collection":
                    Settings.COLLECTION_NAME,

                "host":
                    Settings.QDRANT_HOST,

                "port":
                    Settings.QDRANT_PORT,

                "distance_metric":
                    Settings.DISTANCE_METRIC,

            },

            "processing": {

                "metadata_extracted": True,

                "text_extracted": True,

                "text_cleaned": True,

                "text_chunked": True,

                "chunk_validation": True,

                "ocr_enabled": True,

                "images_extracted": True,

                "tables_extracted": True,

            },

        }

        return report

    def save(
        self,
        report: dict[str, Any],
    ) -> Path:
        """
        Save report as JSON.
        """

        output_path = (
            Settings.REPORT_DIR
            / f"{self.pdf_path.stem}_report.json"
        )

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False,
            )

        return output_path