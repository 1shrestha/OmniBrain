from src.retrieval.retriever import Retriever

retriever = Retriever()

results = retriever.retrieve(
    "What is the total revenue?"
)

for result in results:
    print("-" * 80)
    print(result["score"])
    print(result["document"])
    print(result["page_number"])
    print(result["text"])