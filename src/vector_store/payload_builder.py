"""
OmniBrain - Payload Builder

Module:
    Payload Builder

Purpose:
    Build standardized payloads for Qdrant vector storage.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from configs.settings import Settings


class PayloadBuilder:
    """
    Build Qdrant payloads from embedding data.
    """

    def __init__(self):

        self.logger = logging.getLogger(__name__)

        Settings.PAYLOAD_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

    # ---------------------------------------------------------

    def build(
        self,
        embedding_file: str | Path
    ) -> list[dict[str, Any]]:
        """
        Build payloads from embedding JSON.

        Args:
            embedding_file:
                Path to embedding JSON.

        Returns:
            List of Qdrant payload objects.
        """

        embedding_file = Path(embedding_file)

        with open(
            embedding_file,
            "r",
            encoding="utf-8"
        ) as f:
            embeddings = json.load(f)

        payloads = []

        for item in embeddings:

            payload = {

                "id": item["chunk_id"],

                "vector": item["embedding"],

                "payload": {

                    "document_id": item["document_id"],

                    "document": item["document"],

                    "page_number": item["page_number"],

                    "chunk_index": item["chunk_index"],

                    "embedding_model": item["embedding_model"],

                    "dimension": item["dimension"]

                }

            }

            payloads.append(payload)

        output_file = (
            Settings.PAYLOAD_DIR
            /
            embedding_file.name.replace(
                "_embeddings",
                "_payloads"
            )
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                payloads,
                f,
                indent=4,
                ensure_ascii=False
            )

        self.logger.info(
            f"Payloads saved to {output_file}"
        )

        return payloads

    # ---------------------------------------------------------

    @staticmethod
    def count(
        payloads: list[dict]
    ) -> int:
        """
        Return payload count.
        """

        return len(payloads)