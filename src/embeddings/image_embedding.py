"""
OmniBrain - Image Embedding Generator

Generate OpenCLIP embeddings for extracted images.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import open_clip
import torch
from PIL import Image

from configs.settings import Settings


class ImageEmbeddingGenerator:
    """Generate image embeddings from extracted image metadata."""

    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        logging.info(f"Loading OpenCLIP on {self.device}")

        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            Settings.IMAGE_EMBEDDING_MODEL,
            pretrained=Settings.IMAGE_PRETRAINED,
            device=self.device,
        )

        self.model.eval()

    def generate_embedding(self, image_path: str | Path) -> list[float]:
        image = Image.open(image_path).convert("RGB")

        image_tensor = (
            self.preprocess(image)
            .unsqueeze(0)
            .to(self.device)
        )

        with torch.no_grad():
            embedding = self.model.encode_image(image_tensor)
            embedding /= embedding.norm(dim=-1, keepdim=True)

        return embedding.squeeze().cpu().tolist()

    def _extract_image_name(self, relative_path: str) -> str:
        return Path(relative_path).name

    def _absolute_path(self, relative_path: str) -> Path:
        return Settings.PROJECT_ROOT / relative_path

    def _extract_page(self, image_name: str) -> int:
        m = re.search(r"page_(\d+)", image_name)
        return int(m.group(1)) if m else -1

    def generate_embeddings(
        self,
        image_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate embeddings using ImageExtractor metadata.
        """

        embeddings: list[dict[str, Any]] = []

        images = image_data.get("images", [])

        logging.info(f"Found {len(images)} extracted image(s).")

        for item in images:

            try:
                image_path = self._absolute_path(item["path"])

                if not image_path.exists():
                    logging.warning(f"Missing image: {image_path}")
                    continue

                vector = self.generate_embedding(image_path)

                embeddings.append(
                    {
                        "image_id": item["image_id"],
                        "document_id": item["document_id"],
                        "document": item["document"],
                        "page_number": item["page_number"],
                        "image_index": item["image_index"],
                        "image_name": self._extract_image_name(item["path"]),
                        "image_path": str(image_path),
                        "width": item["width"],
                        "height": item["height"],
                        "format": item["format"],
                        "embedding_model": Settings.IMAGE_EMBEDDING_MODEL,
                        "dimension": len(vector),
                        "embedding": vector,
                    }
                )

            except Exception as exc:
                logging.exception(
                    f"Failed to embed {item.get('path')}: {exc}"
                )

        logging.info(
            f"Generated {len(embeddings)} image embedding(s)."
        )

        return embeddings
