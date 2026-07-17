"""
OmniBrain - PDF Ingestion Engine

File: settings.py

Purpose:
    Centralized configuration for project paths,
    processing, embeddings, vector database,
    and retrieval.
"""

from pathlib import Path


class Settings:
    """
    Application configuration.
    """

    # Project Root

    PROJECT_ROOT = Path(__file__).resolve().parent.parent

    # Data Directories

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

    TEMP_DIR = DATA_DIR / "temp"

    # Logs

    LOG_DIR = PROJECT_ROOT / "logs"

    # Supported File Types

    SUPPORTED_EXTENSIONS = [
        ".pdf",
    ]

    # OCR Configuration

    OCR_THRESHOLD = 30

    OCR_DPI = 2.0

    OCR_LANGUAGES = [
        "en",
    ]

    OCR_GPU = False

    # Image Extraction

    IMAGE_FORMAT = "png"

    # Text Chunking Configuration

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

    # Embedding Configuration

    EMBEDDING_MODEL = (
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    EMBEDDING_DEVICE = "cpu"

    EMBEDDING_BATCH_SIZE = 32

    NORMALIZE_EMBEDDINGS = True

    VECTOR_DIMENSION = 384

    EMBEDDING_FILE = "embeddings.json"

    # Vector Database Configuration

    QDRANT_HOST = "localhost"

    QDRANT_PORT = 6333

    COLLECTION_NAME = "omnibrain_documents"

    DISTANCE_METRIC = "Cosine"

    QDRANT_BATCH_SIZE = 100

    RECREATE_COLLECTION = False

    # Retrieval Configuration

    TOP_K_RESULTS = 5

    SIMILARITY_THRESHOLD = 0.65

    # Utility Methods

    @classmethod
    def create_directories(cls) -> None:
        """
        Create all required project directories.
        """

        directories = [
            cls.INPUT_PDF_DIR,
            cls.TEXT_DIR,
            cls.IMAGE_DIR,
            cls.TABLE_DIR,
            cls.METADATA_DIR,
            cls.REPORT_DIR,
            cls.CHUNK_OUTPUT_DIR,
            cls.EMBEDDING_DIR,
            cls.TEMP_DIR,
            cls.LOG_DIR,
        ]

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )