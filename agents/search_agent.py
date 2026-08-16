from typing import Dict, Any

class SearchAgent:
    def __init__(self, vector_store):
        self.store = vector_store

    def run(self, query: str) -> Dict[str, Any]:
        # Use the provided vector store for a mock similarity search when available
        try:
            results = self.store.similarity_search(query, k=3)
        except Exception:
            results = []

        answer = None
        citations = []
        if results:
            # Prefer text field if present
            first = results[0]
            answer = first.get("text") or first.get("description") or "Mock search answer"
            for r in results:
                citations.append({"source": r.get("metadata", {}).get("source", "mock")})
        else:
            answer = "Mock search answer"

        return {"answer": answer, "citations": citations}
