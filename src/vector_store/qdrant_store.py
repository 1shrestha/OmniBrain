"""
OmniBrain - Qdrant Vector Store

Manage all interactions with the Qdrant vector database.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from configs.settings import Settings
from src.vector_store.client_manager import ClientManager


class QdrantStore:
    """Qdrant Vector Database Manager."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = ClientManager.get_client()

        if Settings.RECREATE_COLLECTION:
            self._recreate_collections()

    @staticmethod
    def _distance_metric() -> Distance:
        mapping = {
            "Cosine": Distance.COSINE,
            "Dot": Distance.DOT,
            "Euclid": Distance.EUCLID,
            "Manhattan": Distance.MANHATTAN,
        }
        return mapping.get(Settings.DISTANCE_METRIC, Distance.COSINE)

    def _collection_exists(self, name: str) -> bool:
        collections = self.client.get_collections().collections
        return any(c.name == name for c in collections)

    def _create_collection(self, name: str, size: int):
        if self._collection_exists(name):
            return

        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=size,
                distance=self._distance_metric(),
            ),
        )

    def _recreate_collections(self):
        """Recreate text and image collections when enabled in settings."""
        for collection in (
            Settings.QDRANT_COLLECTION,
            Settings.IMAGE_COLLECTION,
        ):
            if self._collection_exists(collection):
                self.logger.info("Deleting existing collection: %s", collection)
                self.client.delete_collection(collection)

        self.logger.info("Qdrant collections recreated.")

    def upload_embeddings(self, embeddings: list[dict[str, Any]]):
        if not embeddings:
            return

        self._create_collection(
            Settings.QDRANT_COLLECTION,
            len(embeddings[0]["embedding"]),
        )

        points = []

        for item in embeddings:
            payload = {
                "chunk_id": item["chunk_id"],
                "document_id": item["document_id"],
                "document": item["document"],
                "page_number": item["page_number"],
                "chunk_index": item["chunk_index"],
                "text": item["text"],
                "embedding_model": item["embedding_model"],
                "dimension": item["dimension"],
                "modality": "text",
            }

            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, item["chunk_id"])),
                    vector=item["embedding"],
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=Settings.QDRANT_COLLECTION,
            points=points,
            wait=True,
        )

    def upload_image_embeddings(self, embeddings: list[dict[str, Any]]) -> int:
        if not embeddings:
            return 0

        self._create_collection(
            Settings.IMAGE_COLLECTION,
            len(embeddings[0]["embedding"]),
        )

        points = []

        for item in embeddings:
            payload = {
                "image_id": item["image_id"],
                "document_id": item["document_id"],
                "document": item["document"],
                "page_number": item["page_number"],
                "image_index": item["image_index"],
                "image_name": item["image_name"],
                "image_path": item["image_path"],
                "width": item["width"],
                "height": item["height"],
                "format": item["format"],
                "embedding_model": item["embedding_model"],
                "dimension": item["dimension"],
                "modality": "image",
            }

            points.append(
                PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_DNS, item["image_id"])),
                    vector=item["embedding"],
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=Settings.IMAGE_COLLECTION,
            points=points,
            wait=True,
        )

        self.logger.info(
            "Uploaded %d image vectors.", len(points)
        )

        return len(points)

    def count_vectors(self):
        return self.client.count(
            collection_name=Settings.QDRANT_COLLECTION,
            exact=True,
        ).count

    def search(self, query_vector, limit=Settings.SEARCH_LIMIT):
        return self.client.query_points(
            collection_name=Settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=limit,
            with_payload=True,
        ).points

    def search_document(self, document_id):
        return self.client.scroll(
            collection_name=Settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
            with_payload=True,
        )

    def delete_collection(self):
        if self._collection_exists(Settings.QDRANT_COLLECTION):
            self.client.delete_collection(Settings.QDRANT_COLLECTION)

    def health_check(self):
        try:
            self.client.get_collections()
            return True
        except Exception:
            self.logger.exception("Qdrant health check failed.")
            return False
