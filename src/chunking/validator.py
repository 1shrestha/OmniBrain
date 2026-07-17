"""
OmniBrain

Module: Chunk Validator

Purpose:
    Validate generated chunks before embedding
    and vector database storage.
"""

from __future__ import annotations

from typing import Any

from configs.settings import Settings


class ChunkValidator:
    """
    Validate generated chunks.
    """

    def validate(
        self,
        chunk_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Validate generated chunks.
        """

        validated_chunks = []

        previous_chunk = None

        seen_chunks = set()

        removed_empty = 0

        removed_duplicates = 0

        merged_chunks = 0

        original_chunk_count = len(
            chunk_data["chunks"]
        )

        for chunk in chunk_data["chunks"]:

            text = chunk["text"].strip()

            if not text:

                removed_empty += 1

                continue

            fingerprint = (
                chunk["page_number"],
                text,
            )

            if fingerprint in seen_chunks:

                removed_duplicates += 1

                continue

            seen_chunks.add(
                fingerprint
            )

            chunk["text"] = text

            chunk["char_count"] = len(
                text
            )

            chunk["word_count"] = len(
                text.split()
            )

            if (

                previous_chunk is not None

                and previous_chunk["page_number"]
                == chunk["page_number"]

                and chunk["char_count"]
                < Settings.MIN_CHUNK_SIZE

            ):

                previous_chunk["text"] = (
                    previous_chunk["text"].rstrip()
                    + "\n\n"
                    + text
                )

                previous_chunk["char_count"] = len(
                    previous_chunk["text"]
                )

                previous_chunk["word_count"] = len(
                    previous_chunk["text"].split()
                )

                merged_chunks += 1

                continue

            validated_chunks.append(
                chunk
            )

            previous_chunk = chunk

        statistics = self._statistics(
            validated_chunks
        )

        statistics["original_chunk_count"] = (
            original_chunk_count
        )

        statistics["validated_chunk_count"] = len(
            validated_chunks
        )

        statistics["removed_empty"] = (
            removed_empty
        )

        statistics["removed_duplicates"] = (
            removed_duplicates
        )

        statistics["merged_chunks"] = (
            merged_chunks
        )

        return {

            "document_id": chunk_data[
                "document_id"
            ],

            "document": chunk_data[
                "document"
            ],

            "chunk_count": len(
                validated_chunks
            ),

            "statistics": statistics,

            "chunks": validated_chunks,
        }

    def _statistics(
        self,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate chunk statistics.
        """

        if not chunks:

            return {

                "largest_chunk": 0,

                "smallest_chunk": 0,

                "average_chunk_size": 0,

                "average_word_count": 0,

                "total_characters": 0,

                "total_words": 0,

            }

        character_sizes = [

            chunk["char_count"]

            for chunk in chunks

        ]

        word_sizes = [

            chunk["word_count"]

            for chunk in chunks

        ]

        return {

            "largest_chunk": max(
                character_sizes
            ),

            "smallest_chunk": min(
                character_sizes
            ),

            "average_chunk_size": round(
                sum(character_sizes)
                / len(character_sizes),
                2,
            ),

            "average_word_count": round(
                sum(word_sizes)
                / len(word_sizes),
                2,
            ),

            "total_characters": sum(
                character_sizes
            ),

            "total_words": sum(
                word_sizes
            ),
        }