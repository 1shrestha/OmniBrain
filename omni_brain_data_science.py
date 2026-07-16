from sentence_transformers import SentenceTransformer
import time

#load the model
model = SentenceTransformer("all-MiniLM-L6-v2")
#using sample data
documents = [
    "welcome to omni brain "
    "a multilevel ai model"
    "not a simple chatboat"
    "answering your questions"
]

#generate embeddings

embeddings = model.encode(documents)

#printing embeddings

print(embeddings)

#inspecting embeddings

print(type(embeddings))
print(len(embeddings))
print(len(embeddings[0]))
print(embeddings.shape)

#create query for embedding

query = "what is omni brain"
query_embedding = model.encode(query)
print(query_embedding.shape)

#creating second model

model2 = SentenceTransformer("paraphrase-MiniLM-L3-v2")
start = time.time()
embeddings2 = model2.encode(documents)
end = time.time()
print("Model 2")
print("Name: paraphrase-MiniLM-L3-v2")
print("Shape:", embeddings2.shape)
print("Time:", end - start)
print("Memory:", embeddings2.nbytes, "bytes")
