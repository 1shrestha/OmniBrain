"""
OmniBrain - Qdrant Client Manager

Centralized Qdrant client management.

Responsibilities:
    - Create only one Qdrant client
    - Support embedded and server modes
    - Reuse the same client across the application
"""

from __future__ import annotations

import logging

from qdrant_client import QdrantClient

from configs.settings import Settings


class ClientManager:
    """
    Singleton manager for the Qdrant client.
    """

    _client: QdrantClient | None = None

    @classmethod
    def get_client(cls) -> QdrantClient:
        """
        Return the shared Qdrant client.
        """

        if cls._client is None:

            logger = logging.getLogger(__name__)

            if Settings.VECTOR_DB_MODE.lower() == "local":

                Settings.VECTOR_DB_DIR.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                cls._client = QdrantClient(
                    path=str(Settings.VECTOR_DB_DIR)
                )

                logger.info(
                    f"Using embedded Qdrant at "
                    f"{Settings.VECTOR_DB_DIR}"
                )

            else:

                cls._client = QdrantClient(
                    host=Settings.QDRANT_HOST,
                    port=Settings.QDRANT_PORT,
                )

                logger.info(
                    f"Connected to Qdrant server "
                    f"{Settings.QDRANT_HOST}:{Settings.QDRANT_PORT}"
                )

        return cls._client

    @classmethod
    def close_client(cls) -> None:
        """
        Close the shared Qdrant client.
        """

        if cls._client is not None:

            try:

                cls._client.close()

            except AttributeError:
                # Local Qdrant may not expose close()
                pass

            cls._client = None

            logging.info(
                "Qdrant client released."
            )