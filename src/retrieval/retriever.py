"""
OmniBrain - Retriever

Generate query embeddings and retrieve the most relevant
document chunks from the vector database.
"""

from __future__ import annotations

import logging

import torch
from typing import Any

from configs.settings import Settings
from src.models.model_manager import ModelManager
from src.vector_store.qdrant_store import QdrantStore


class Retriever:
    """
    Semantic Retriever.

    Responsibilities:
        - Generate query embeddings
        - Perform semantic search
        - Return retrieved chunks
    """

    def __init__(
        self,
        store: QdrantStore,
    ):
        """
        Initialize the retriever.

        Args:
            store:
                Shared QdrantStore instance.
        """

        self.logger = logging.getLogger(__name__)

        # Shared embedding model
        self.model = ModelManager.get_embedding_model()

        # Shared vector store
        self.store = store

    # ---------------------------------------------------------

    def embed_query(
        self,
        query: str,
    ) -> list[float]:
        """
        Convert a query into an embedding vector.
        """

        with torch.inference_mode():

            vector = self.model.encode(
                query,
                normalize_embeddings=Settings.NORMALIZE_EMBEDDINGS,
                convert_to_numpy=True,
            )

        return vector.tolist()

    # ---------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant chunks.
        """

        if top_k is None:
            top_k = Settings.TOP_K_RESULTS

        query_vector = self.embed_query(query)

        results = self.store.search(
            query_vector=query_vector,
            limit=top_k,
        )

        retrieved = []

        for result in results:

            if result.score < Settings.SIMILARITY_THRESHOLD:
                continue

            payload = result.payload

            retrieved.append(
                {
                    "score": result.score,
                    "chunk_id": payload.get("chunk_id"),
                    "document_id": payload.get("document_id"),
                    "document": payload.get("document"),
                    "page_number": payload.get("page_number"),
                    "chunk_index": payload.get("chunk_index"),
                    "text": payload.get("text"),
                }
            )

        self.logger.info(
            f'Query: "{query}" | Retrieved {len(retrieved)} chunks.'
        )

        return retrieved

    # ---------------------------------------------------------

    def retrieve_context(
        self,
        query: str,
        top_k: int | None = None,
    ) -> str:
        """
        Retrieve context as a single string.
        """

        chunks = self.retrieve(
            query=query,
            top_k=top_k,
        )

        if not chunks:
            return ""

        return "\n\n".join(
            chunk["text"]
            for chunk in chunks
        )

    # ---------------------------------------------------------

    def retrieve_document(
        self,
        document_id: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve all chunks belonging to a document.
        """

        results, _ = self.store.search_document(
            document_id=document_id,
        )

        documents = []

        for point in results:

            payload = point.payload

            documents.append(
                {
                    "chunk_id": payload.get("chunk_id"),
                    "document_id": payload.get("document_id"),
                    "document": payload.get("document"),
                    "page_number": payload.get("page_number"),
                    "chunk_index": payload.get("chunk_index"),
                    "text": payload.get("text"),
                }
            )

        self.logger.info(
            f"Retrieved {len(documents)} chunks from '{document_id}'."
        )

        return documents