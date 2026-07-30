"""
OmniBrain - RAG Pipeline Test

Tests the complete Retrieval-Augmented Generation (RAG) pipeline.

Workflow:
    Chunk File
        ↓
    Embedding Generation
        ↓
    Vector Database
        ↓
    Semantic Retrieval
"""

from configs.settings import Settings

from src.embeddings.embedding_generator import EmbeddingGenerator
from src.retrieval.retriever import Retriever
from src.vector_store.qdrant_store import QdrantStore


def main():

    chunk_file = (
        Settings.CHUNK_OUTPUT_DIR
        /
        "NASDAQ_WEYS_2024_chunks.json"
    )

    print("\nGenerating Embeddings...")

    generator = EmbeddingGenerator()

    embeddings = generator.generate(
        chunk_file
    )

    print(
        f"Generated {len(embeddings)} embeddings."
    )

    print("\nUploading to Vector Database...")

    # Shared Vector Store
    store = QdrantStore()

    store.upload_embeddings(
        embeddings
    )

    print(
        f"Vectors Stored : {store.count_vectors()}"
    )

    print("\nTesting Semantic Retrieval...\n")

    # Pass the shared store to Retriever
    retriever = Retriever(
        store=store
    )

    results = retriever.retrieve(
        query="Summarize the annual report.",
        top_k=5,
    )

    if not results:

        print("No results found.")

        return

    for index, result in enumerate(
        results,
        start=1,
    ):

        print("-" * 80)

        print(f"Result {index}")

        print(f"Score      : {result['score']:.4f}")

        print(f"Document   : {result['document']}")

        print(f"Page       : {result['page_number']}")

        print(f"Chunk      : {result['chunk_index']}")

        print()

        print(result["text"])

        print()

    print("-" * 80)

    print("\nPipeline Test Completed Successfully.")


if __name__ == "__main__":

    main()