from app.database.vector_store import VectorStore


def test_vector_store_initializes_without_chromadb() -> None:
    store = VectorStore()

    store.add_chunks(
        chunk_ids=["chunk-1"],
        embeddings=[[0.1, 0.2, 0.3]],
        texts=["sample text"],
        metadatas=[{"document_id": "doc-1", "page_number": 1, "chunk_index": 0}],
    )

    results = store.search([0.1, 0.2, 0.3], top_k=1)

    assert store.count() == 1
    assert results[0]["metadata"]["document_id"] == "doc-1"
    assert results[0]["similarity"] >= 0.95
