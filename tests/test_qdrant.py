from src.embeddings.embedding_generator import EmbeddingGenerator
from src.vector_store.qdrant_store import QdrantStore

generator = EmbeddingGenerator()

embeddings = generator.generate(
    "data/processed/chunks/NASDAQ_WEYS_2024_chunks.json"
)

store = QdrantStore()

store.upload_embeddings(embeddings)

print(store.count_vectors())