import numpy as np
import os
import re
from typing import List, Dict, Any, Union
from config import IS_MOCK

class MultiModalVectorStore:
    def __init__(self, is_mock: bool = IS_MOCK):
        self.is_mock = is_mock
        self.texts = []  # List[Dict[str, Any]]
        self.images = []  # List[Dict[str, Any]]
        self.dimension = 1536  # Default dimension for embeddings
        
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.qdrant_client = None
        
        if self.qdrant_url and not self.is_mock:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.models import VectorParams, Distance
                
                self.qdrant_client = QdrantClient(
                    url=self.qdrant_url,
                    api_key=self.qdrant_api_key
                )
                
                # Check and create collections
                for col in ["omnibrain_texts", "omnibrain_images"]:
                    try:
                        self.qdrant_client.get_collection(col)
                    except Exception:
                        self.qdrant_client.create_collection(
                            collection_name=col,
                            vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE)
                        )
                print(f"[Qdrant] Connected to {self.qdrant_url}")
            except Exception as e:
                print(f"[Qdrant] Initialization failed: {e}. Using in-memory mode.")
                self.qdrant_client = None

    def _get_embedding(self, text: str) -> np.ndarray:
        if self.is_mock:
            np.random.seed(abs(hash(text)) % (2**32))
            vec = np.random.randn(self.dimension)
            norm = np.linalg.norm(vec)
            return vec / (norm if norm > 0 else 1.0)
        else:
            try:
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings()
                return np.array(embeddings.embed_query(text))
            except Exception as e:
                np.random.seed(abs(hash(text)) % (2**32))
                vec = np.random.randn(self.dimension)
                norm = np.linalg.norm(vec)
                return vec / (norm if norm > 0 else 1.0)

    def add_text(self, text: str, metadata: Dict[str, Any] = None):
        emb = self._get_embedding(text)
        item = {
            "text": text,
            "metadata": metadata or {},
            "embedding": emb,
            "type": "text"
        }
        self.texts.append(item)
        
        if self.qdrant_client:
            try:
                from qdrant_client.models import PointStruct
                import uuid
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, text))
                self.qdrant_client.upsert(
                    collection_name="omnibrain_texts",
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=emb.tolist(),
                            payload={
                                "text": text,
                                "metadata": metadata or {},
                                "type": "text"
                            }
                        )
                    ]
                )
            except Exception as e:
                print(f"[Qdrant] add_text failed: {e}")

    def add_image(self, image_path: str, description: str, metadata: Dict[str, Any] = None):
        emb = self._get_embedding(description)
        item = {
            "image_path": image_path,
            "description": description,
            "metadata": metadata or {},
            "embedding": emb,
            "type": "image"
        }
        self.images.append(item)
        
        if self.qdrant_client:
            try:
                from qdrant_client.models import PointStruct
                import uuid
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, image_path))
                self.qdrant_client.upsert(
                    collection_name="omnibrain_images",
                    points=[
                        PointStruct(
                            id=point_id,
                            vector=emb.tolist(),
                            payload={
                                "image_path": image_path,
                                "description": description,
                                "metadata": metadata or {},
                                "type": "image"
                            }
                        )
                    ]
                )
            except Exception as e:
                print(f"[Qdrant] add_image failed: {e}")

    def similarity_search(self, query: str, k: int = 3, type_filter: str = None) -> List[Dict[str, Any]]:
        if self.qdrant_client and not self.is_mock:
            try:
                query_emb = self._get_embedding(query)
                collections = []
                if type_filter in [None, "text"]:
                    collections.append("omnibrain_texts")
                if type_filter in [None, "image"]:
                    collections.append("omnibrain_images")
                
                qdrant_results = []
                for col in collections:
                    hits = self.qdrant_client.search(
                        collection_name=col,
                        query_vector=query_emb.tolist(),
                        limit=k
                    )
                    for hit in hits:
                        res = hit.payload.copy()
                        res["score"] = hit.score
                        qdrant_results.append(res)
                        
                qdrant_results.sort(key=lambda x: x["score"], reverse=True)
                return qdrant_results[:k]
            except Exception as e:
                print(f"[Qdrant] Search failed: {e}. Falling back to memory search.")

        candidates = []
        if type_filter in [None, "text"]:
            candidates.extend(self.texts)
        if type_filter in [None, "image"]:
            candidates.extend(self.images)
            
        if not candidates:
            return []
            
        results = []
        if self.is_mock:
            query_words = set(re.findall(r'\w+', query.lower()))
            for item in candidates:
                content = item["text"].lower() if item["type"] == "text" else item["description"].lower()
                content_words = set(re.findall(r'\w+', content))
                overlap = len(query_words.intersection(content_words))
                tie_breaker = (abs(hash(content)) % 1000) / 10000.0
                score = float(overlap) + tie_breaker
                results.append((score, item))
        else:
            query_emb = self._get_embedding(query)
            for item in candidates:
                item_emb = item["embedding"]
                similarity = float(np.dot(query_emb, item_emb))
                results.append((similarity, item))
            
        results.sort(key=lambda x: x[0], reverse=True)
        
        formatted_results = []
        for score, item in results[:k]:
            res = item.copy()
            if "embedding" in res:
                res.pop("embedding")
            res["score"] = score
            formatted_results.append(res)
            
        return formatted_results

