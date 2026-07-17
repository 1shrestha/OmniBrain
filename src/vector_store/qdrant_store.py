"""
OmniBrain - Qdrant Vector Store

Manage all interactions with the Qdrant vector database.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.vector_store.client_manager import ClientManager
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from configs.settings import Settings


class QdrantStore:
    """Qdrant Vector Database Manager."""

    def __init__(self):
        """
        Initialize the vector store.

        The Qdrant client is provided by ClientManager,
        ensuring only one client exists throughout the application.
        """

        self.logger = logging.getLogger(__name__)

        self.client = ClientManager.get_client()

        self.collection_name = Settings.QDRANT_COLLECTION

    def collection_exists(self) -> bool:
        """Return True if the collection exists."""

        collections = self.client.get_collections().collections

        return any(
            collection.name == self.collection_name
            for collection in collections
        )

    def create_collection(
        self,
        vector_size: int,
    ) -> None:
        """Create collection if it does not exist."""

        if self.collection_exists():

            self.logger.info(
                f"Collection '{self.collection_name}' already exists."
            )

            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        self.logger.info(
            f"Collection '{self.collection_name}' created."
        )

    def recreate_collection(
        self,
        vector_size: int,
    ) -> None:
        """Delete and recreate the collection."""

        if self.collection_exists():

            self.client.delete_collection(
                collection_name=self.collection_name
            )

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )

        self.logger.info(
            f"Collection '{self.collection_name}' recreated."
        )

    def upload_embeddings(
        self,
        embeddings: list[dict[str, Any]],
    ) -> None:
        """Upload embeddings to Qdrant."""

        if not embeddings:

            self.logger.warning(
                "No embeddings found."
            )

            return

        vector_size = len(
            embeddings[0]["embedding"]
        )

        if Settings.RECREATE_COLLECTION:
            self.recreate_collection(vector_size)
        else:
            self.create_collection(vector_size)

        points = []

        for item in embeddings:

            payload = {
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "document": item["document"],
                "page_number": item["page_number"],
                "chunk_index": item["chunk_index"],
                "text": item["text"],
            }

            point_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    item["chunk_id"],
                )
            )

            points.append(
                PointStruct(
                    id=point_id,
                    vector=item["embedding"],
                    payload=payload,
                )
            )

        batch_size = Settings.QDRANT_BATCH_SIZE

        for start in range(
            0,
            len(points),
            batch_size,
        ):

            batch = points[
                start:start + batch_size
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
                wait=True,
            )

            self.logger.info(
                f"Uploaded {len(batch)} vectors."
            )

        self.logger.info(
            f"Successfully uploaded {len(points)} vectors."
        )

    def search(
    self,
    query_vector: list[float],
    limit: int = Settings.SEARCH_LIMIT,
    ):
        """
        Perform semantic search.
        Compatible with qdrant-client >= 1.18.
        """

        response = self.client.query_points(
        collection_name=self.collection_name,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )

        return response.points

    def search_document(
        self,
        document_id: str,
    ):
        """Return all vectors belonging to a document."""

        return self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(
                            value=document_id,
                        ),
                    )
                ]
            ),
            with_payload=True,
        )

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        """Delete all vectors belonging to a document."""

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(
                            value=document_id,
                        ),
                    )
                ]
            ),
        )

        self.logger.info(
            f"Deleted document '{document_id}'."
        )

    def delete_collection(self) -> None:
        """Delete the collection."""

        if not self.collection_exists():
            return

        self.client.delete_collection(
            collection_name=self.collection_name,
        )

        self.logger.info(
            f"Deleted collection '{self.collection_name}'."
        )

    def count_vectors(self) -> int:
        """Return the number of stored vectors."""

        response = self.client.count(
            collection_name=self.collection_name,
            exact=True,
        )

        return response.count

    def health_check(self) -> bool:
        """Verify Qdrant connection."""

        try:

            self.client.get_collections()

            self.logger.info(
                "Qdrant connection successful."
            )

            return True

        except Exception as error:

            self.logger.error(error)

            return False