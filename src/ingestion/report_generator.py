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

    def __init__(self, pdf_path: Path) -> None:
        self.pdf_path = Path(pdf_path)

    def generate(
        self,
        metadata: dict[str, Any],
        text: dict[str, Any],
        chunks: dict[str, Any],
        images: dict[str, Any],
        tables: dict[str, Any],
        text_embeddings: int,
        text_vectors_uploaded: int,
        image_embeddings: int,
        image_vectors_uploaded: int,
    ) -> dict[str, Any]:
        """
        Generate ingestion report.
        """

        report = {

            "document_id": metadata["document_id"],
            "document": self.pdf_path.name,
            "generated_at": datetime.now().isoformat(),
            "status": "SUCCESS",
            "pipeline_version": "3.0",

            "metadata": metadata,

            "summary": {
                "pages": metadata["pages"],
                "characters": text["total_characters"],
                "empty_pages": len(text["empty_pages"]),
                "ocr_pages": text["ocr_pages"],
                "chunks": chunks["chunk_count"],
                "images": images["unique_images"],
                "tables": tables["count"],
                "text_embeddings": text_embeddings,
                "text_vectors_uploaded": text_vectors_uploaded,
                "image_embeddings": image_embeddings,
                "image_vectors_uploaded": image_vectors_uploaded,
            },

            "chunk_statistics": chunks["statistics"],

            "image_statistics": {
                "total_images": images["count"],
                "unique_images": images["unique_images"],
                "image_embeddings": image_embeddings,
                "image_vectors_uploaded": image_vectors_uploaded,
            },

            "table_statistics": {
                "total_tables": tables["count"],
            },

            "embedding_configuration": {
                "text_embedding_model": Settings.EMBEDDING_MODEL,
                "text_vector_dimension": Settings.VECTOR_DIMENSION,
                "image_embedding_model": Settings.IMAGE_EMBEDDING_MODEL,
                "image_vector_dimension": Settings.IMAGE_VECTOR_DIMENSION,
                "normalized": Settings.NORMALIZE_EMBEDDINGS,
                "device": Settings.EMBEDDING_DEVICE,
            },

            "vector_database": {
                "provider": "Qdrant",
                "text_collection": Settings.QDRANT_COLLECTION,
                "image_collection": Settings.IMAGE_COLLECTION,
                "host": Settings.QDRANT_HOST,
                "port": Settings.QDRANT_PORT,
                "distance_metric": Settings.DISTANCE_METRIC,
            },

            "processing": {
                "metadata_extracted": True,
                "text_extracted": True,
                "text_cleaned": True,
                "text_chunked": True,
                "chunk_validation": True,
                "text_embeddings_generated": True,
                "text_vectors_uploaded": True,
                "ocr_enabled": True,
                "images_extracted": True,
                "image_embeddings_generated": True,
                "image_vectors_uploaded": True,
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
