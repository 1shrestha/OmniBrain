import pytest
from retrieval import MultiModalVectorStore

def test_vector_store_addition_and_search():
    """Verifies document indexing and similarity search in MultiModalVectorStore."""
    store = MultiModalVectorStore(is_mock=True)
    
    # Add items
    store.add_text("Quarterly earnings are positive.", {"source": "earnings.txt"})
    store.add_image("chart.png", "Revenue chart showing quarterly growth.", {"source": "chart.png"})
    
    # Verify both added
    assert len(store.texts) == 1
    assert len(store.images) == 1

    # Similarity search general query
    results_all = store.similarity_search("quarterly earnings and growth", k=2)
    assert len(results_all) == 2
    
    # Similarity search with text filter
    results_text = store.similarity_search("quarterly earnings", k=2, type_filter="text")
    assert len(results_text) == 1
    assert results_text[0]["type"] == "text"
    assert results_text[0]["text"] == "Quarterly earnings are positive."
    
    # Similarity search with image filter
    results_img = store.similarity_search("quarterly growth", k=2, type_filter="image")
    assert len(results_img) == 1
    assert results_img[0]["type"] == "image"
    assert results_img[0]["image_path"] == "chart.png"
