from src.embeddings.embedding_generator import EmbeddingGenerator

generator = EmbeddingGenerator()

embeddings = generator.generate(
    "data/processed/chunks/NASDAQ_WEYS_2024_chunks.json"
)

print(f"Generated {len(embeddings)} embeddings")

print(embeddings[0].keys())