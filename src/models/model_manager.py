"""
OmniBrain - Model Manager

Centralized model loading and management.

Responsibilities:
    - Load AI models only once
    - Automatically select CPU/GPU
    - Share model instances
    - Support future Embedding, Reranker,
      Vision and LLM models
"""

from __future__ import annotations

import logging
import threading

import torch
from sentence_transformers import SentenceTransformer

from configs.settings import Settings


class ModelManager:
    """
    Singleton manager for all AI models.

    Models are loaded once and shared
    across the entire application.
    """

    _embedding_model: SentenceTransformer | None = None

    _lock = threading.Lock()

    logger = logging.getLogger(__name__)

    @classmethod
    def get_embedding_model(cls) -> SentenceTransformer:
        """
        Return the shared embedding model.
        """

        if cls._embedding_model is None:

            with cls._lock:

                if cls._embedding_model is None:

                    cls.logger.info(
                        "Loading embedding model: %s",
                        Settings.EMBEDDING_MODEL,
                    )

                    cls.logger.info(
                        "Device: %s",
                        Settings.EMBEDDING_DEVICE,
                    )

                    cls._embedding_model = SentenceTransformer(
                        Settings.EMBEDDING_MODEL,
                        device=Settings.EMBEDDING_DEVICE,
                    )

                    cls.logger.info(
                        "Embedding model loaded successfully."
                    )

        return cls._embedding_model

    @classmethod
    def unload_embedding_model(cls) -> None:
        """
        Release the embedding model.
        """

        if cls._embedding_model is not None:

            cls.logger.info(
                "Unloading embedding model..."
            )

            del cls._embedding_model

            cls._embedding_model = None

            if torch.cuda.is_available():

                torch.cuda.empty_cache()

            cls.logger.info(
                "Embedding model unloaded."
            )

    @staticmethod
    def device() -> str:
        """
        Return the active inference device.
        """

        return Settings.EMBEDDING_DEVICE

    @staticmethod
    def gpu_available() -> bool:
        """
        Return True if CUDA is available.
        """

        return torch.cuda.is_available()

    @staticmethod
    def gpu_name() -> str:
        """
        Return GPU name if available.
        """

        if torch.cuda.is_available():

            return torch.cuda.get_device_name(0)

        return "CPU"