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

#creating third model

model3 = SentenceTransformer("BAAI/bge-small-en-v1.5")
start = time.time()
embeddings3 = model3.encode(documents)
end = time.time()
print("Model 2")
print("Name: paraphrase-MiniLM-L3-v2")
print("Shape:", embeddings3.shape)
print("Time:", end - start)
print("Memory:", embeddings3.nbytes, "bytes")

#creating fourth model

model4 = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
start = time.time()
embeddings4 = model4.encode(documents)
end = time.time()
print("Model4")
print("Name: all-mpnet-base-v2")
print("Shape:", embeddings4.shape)
print("Time:", end - start)
print("Memory:", embeddings4.nbytes, "bytes")

