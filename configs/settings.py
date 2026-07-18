"""OmniBrain Configuration

Centralized application settings for project paths,
OCR, chunking, embeddings, vector database,
retrieval, logging, and hardware configuration.
"""

from __future__ import annotations

from pathlib import Path
import torch


class Settings:
    """Application configuration."""

    # ==========================================================
    # Project Paths
    # ==========================================================

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    DATA_DIR = PROJECT_ROOT / "data"

    INPUT_DIR = DATA_DIR / "input"
    INPUT_PDF_DIR = INPUT_DIR / "pdfs"

    PROCESSED_DIR = DATA_DIR / "processed"

    TEXT_DIR = PROCESSED_DIR / "text"
    IMAGE_DIR = PROCESSED_DIR / "images"
    TABLE_DIR = PROCESSED_DIR / "tables"
    METADATA_DIR = PROCESSED_DIR / "metadata"
    REPORT_DIR = PROCESSED_DIR / "reports"
    CHUNK_OUTPUT_DIR = PROCESSED_DIR / "chunks"
    EMBEDDING_DIR = PROCESSED_DIR / "embeddings"
    PAYLOAD_DIR = PROCESSED_DIR / "payloads"

    VECTOR_DB_DIR = DATA_DIR / "vector_db"

    TEMP_DIR = DATA_DIR / "temp"

    LOG_DIR = PROJECT_ROOT / "logs"
    LOG_FILE = LOG_DIR / "omnibrain.log"
    LOG_LEVEL = "INFO"

    # ==========================================================
    # Hardware Configuration
    # ==========================================================

    USE_GPU = torch.cuda.is_available()
    DEVICE = "cuda" if USE_GPU else "cpu"

    GPU_NAME = (
        torch.cuda.get_device_name(0)
        if USE_GPU
        else "CPU"
    )

    OCR_DEVICE = DEVICE
    EMBEDDING_DEVICE = DEVICE
    RERANKER_DEVICE = DEVICE
    VISION_DEVICE = DEVICE
    LLM_DEVICE = DEVICE
    OCR_GPU = USE_GPU

    # ==========================================================
    # Supported Files
    # ==========================================================

    SUPPORTED_EXTENSIONS = [".pdf"]

    # ==========================================================
    # OCR Configuration
    # ==========================================================

    OCR_THRESHOLD = 30
    OCR_DPI = 2.0
    OCR_LANGUAGES = ["en"]

    # ==========================================================
    # Image Extraction
    # ==========================================================

    IMAGE_FORMAT = "png"

    # ==========================================================
    # Chunking Configuration
    # ==========================================================

    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200

    MIN_CHUNK_SIZE = 150
    MAX_CHUNK_SIZE = 1200

    CHUNK_SEPARATORS = [
        "\n\n",
        "\n",
        ". ",
        " ",
        "",
    ]

    # ==========================================================
    # Text Embedding Configuration
    # ==========================================================

    EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DEVICE = DEVICE
    EMBEDDING_BATCH_SIZE = 32
    NORMALIZE_EMBEDDINGS = True
    VECTOR_DIMENSION = 768
    EMBEDDING_FILE = "embeddings.json"

    # ==========================================================
    # Image Embedding Configuration
    # ==========================================================

    IMAGE_EMBEDDING_MODEL = "ViT-B-32"
    IMAGE_PRETRAINED = "laion2b_s34b_b79k"
    IMAGE_VECTOR_DIMENSION = 512
    IMAGE_BATCH_SIZE = 16
    IMAGE_COLLECTION = "omnibrain_images"

    # ==========================================================
    # Vector Database
    # ==========================================================

    VECTOR_DB_MODE = "local"
    QDRANT_PATH = VECTOR_DB_DIR
    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    QDRANT_COLLECTION = "omnibrain_documents"
    DISTANCE_METRIC = "Cosine"
    QDRANT_BATCH_SIZE = 100
    RECREATE_COLLECTION = False

    # ==========================================================
    # Retrieval
    # ==========================================================

    TOP_K_RESULTS = 5
    SEARCH_LIMIT = 5
    SEARCH_WITH_PAYLOAD = True
    SIMILARITY_THRESHOLD = 0.65

    # ==========================================================
    # Utilities
    # ==========================================================

    @classmethod
    def create_directories(cls) -> None:
        directories = [
            cls.INPUT_PDF_DIR,
            cls.TEXT_DIR,
            cls.IMAGE_DIR,
            cls.TABLE_DIR,
            cls.METADATA_DIR,
            cls.REPORT_DIR,
            cls.CHUNK_OUTPUT_DIR,
            cls.EMBEDDING_DIR,
            cls.PAYLOAD_DIR,
            cls.VECTOR_DB_DIR,
            cls.TEMP_DIR,
            cls.LOG_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def print_device_info(cls) -> None:
        print("\nHardware Configuration")
        print("-" * 30)
        print(f"Device : {cls.DEVICE}")
        print(f"GPU    : {cls.GPU_NAME}")
