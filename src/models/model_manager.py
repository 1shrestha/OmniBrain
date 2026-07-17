"""
OmniBrain - Model Manager

Centralized model loading and management.

Responsibilities:
    - Load embedding models only once
    - Manage CPU/GPU selection
    - Provide shared model instances
    - Support future LLMs and rerankers
"""

from __future__ import annotations

import logging

from sentence_transformers import SentenceTransformer

from configs.settings import Settings


class ModelManager:
    """
    Singleton manager for AI models.

    Ensures that every model is loaded only once
    and shared across the application.
    """

    _embedding_model = None

    def __init__(self):

        self.logger = logging.getLogger(__name__)

    @classmethod
    def get_embedding_model(cls) -> SentenceTransformer:
        """
        Return the shared embedding model.
        """

        if cls._embedding_model is None:

            logging.info(
                f"Loading embedding model: "
                f"{Settings.EMBEDDING_MODEL}"
            )

            cls._embedding_model = SentenceTransformer(
                Settings.EMBEDDING_MODEL,
                device=Settings.EMBEDDING_DEVICE,
            )

            logging.info(
                "Embedding model loaded successfully."
            )

        return cls._embedding_model

    @classmethod
    def unload_embedding_model(cls):
        """
        Release the embedding model.
        """

        cls._embedding_model = None

        logging.info(
            "Embedding model unloaded."
        )