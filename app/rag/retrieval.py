from app.rag.embeddings import model
from app.rag.faiss_store import VectorStore
from app.core.config import DEFAULT_TOP_K
from typing import List, Dict
import numpy as np


def retrieve(query: str, vector_store: VectorStore, top_k: int = DEFAULT_TOP_K) -> List[Dict]:
    """Embed the query and retrieve the most relevant code units."""
    query_embedding = model.encode([query], normalize_embeddings=True)
    query_embedding = np.array(query_embedding, dtype="float32")
    return vector_store.search(query_embedding, top_k)