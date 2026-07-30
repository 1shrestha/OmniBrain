"""
OmniBrain - Embedding Generator

Module:
    Embedding Generator

Purpose:
    Generate dense vector embeddings from validated text chunks
    using Sentence Transformers.

Input:
    data/processed/chunks/<document>_chunks.json

Output:
    data/processed/embeddings/<document>_embeddings.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from configs.settings import Settings
from src.models.model_manager import ModelManager


class EmbeddingGenerator:
    """
    Generate dense embeddings for validated text chunks.
    """

    def __init__(self):

        self.logger = logging.getLogger(__name__)

        # Load shared embedding model
        self.model = ModelManager.get_embedding_model()

        self.batch_size = Settings.EMBEDDING_BATCH_SIZE
        self.normalize = Settings.NORMALIZE_EMBEDDINGS

        Settings.EMBEDDING_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ---------------------------------------------------------

    def generate(
        self,
        chunk_file: str | Path,
    ) -> list[dict[str, Any]]:
        """
        Generate embeddings from a validated chunk file.

        Args:
            chunk_file:
                Path to chunk JSON.

        Returns:
            List of embedding dictionaries.
        """

        chunk_file = Path(chunk_file)

        with open(
            chunk_file,
            "r",
            encoding="utf-8",
        ) as f:

            data = json.load(f)

        chunks = data["chunks"]

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        self.logger.info(
            f"Generating embeddings for {len(texts)} chunks..."
        )

        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )

        embedding_data = []

        for chunk, vector in zip(chunks, vectors):

            embedding_data.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "document": chunk["document"],
                    "page_number": chunk["page_number"],
                    "chunk_index": chunk["chunk_index"],
                    "text": chunk["text"],
                    "embedding_model": Settings.EMBEDDING_MODEL,
                    "dimension": len(vector),
                    "embedding": vector.tolist(),
                }
            )

        output = {
            "document_id": data["document_id"],
            "document": data["document"],
            "embedding_count": len(embedding_data),
            "embeddings": embedding_data,
        }

        output_file = (
            Settings.EMBEDDING_DIR
            / f"{chunk_file.stem.replace('_chunks', '')}_embeddings.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                output,
                f,
                indent=4,
                ensure_ascii=False,
            )

        self.logger.info(
            f"Embeddings saved to {output_file}"
        )

        return embedding_data

    # ---------------------------------------------------------

    def embedding_dimension(self) -> int:
        """
        Return embedding dimension.
        """

        return ModelManager.get_embedding_model().get_sentence_embedding_dimension()

    # ---------------------------------------------------------

    def model_name(self) -> str:
        """
        Return embedding model name.
        """

        return Settings.EMBEDDING_MODEL