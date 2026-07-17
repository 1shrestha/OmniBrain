"""
OmniBrain Configuration

Centralized application settings for project paths,
OCR, chunking, embeddings, vector database,
retrieval, and logging.
"""

from pathlib import Path


class Settings:
    """Application configuration."""

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

    SUPPORTED_EXTENSIONS = [
        ".pdf",
    ]

    OCR_THRESHOLD = 30
    OCR_DPI = 2.0
    OCR_LANGUAGES = ["en"]
    OCR_GPU = False

    IMAGE_FORMAT = "png"

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

    EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
    EMBEDDING_DEVICE = "cpu"
    EMBEDDING_BATCH_SIZE = 32
    NORMALIZE_EMBEDDINGS = True
    VECTOR_DIMENSION = 768
    EMBEDDING_FILE = "embeddings.json"

    VECTOR_DB_MODE = "local"

    QDRANT_HOST = "localhost"
    QDRANT_PORT = 6333
    QDRANT_COLLECTION = "omnibrain_documents"

    DISTANCE_METRIC = "Cosine"
    QDRANT_BATCH_SIZE = 100
    RECREATE_COLLECTION = False

    TOP_K_RESULTS = 5
    SEARCH_LIMIT = 5
    SEARCH_WITH_PAYLOAD = True
    SIMILARITY_THRESHOLD = 0.65

    @classmethod
    def create_directories(cls) -> None:
        """Create all required project directories."""

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
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )