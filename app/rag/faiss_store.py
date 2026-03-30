
import os
import pickle
from typing import Dict, List, Optional

import faiss
import numpy as np

from app.core.config import INDEX_DIR


class VectorStore:
    def __init__(self):
        self.index: Optional[faiss.IndexFlatIP] = None
        self.units: List[Dict] = []

    def build(self, embeddings: np.ndarray, units: List[Dict]):
        """Build a FAISS index from embeddings and their associated code units."""
        dim = embeddings.shape[1]
        # Use Inner Product (cosine similarity since embeddings are normalized)
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self.units = units

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Return the top_k most similar code units."""
        if self.index is None or self.index.ntotal == 0:
            return []
        # Clamp top_k to available vectors
        top_k = min(top_k, self.index.ntotal)
        D, I = self.index.search(query_embedding, top_k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            unit = self.units[idx].copy()
            unit["score"] = float(score)
            results.append(unit)
        return results

    def save(self, repo_name: str):
        """Persist the FAISS index and metadata to disk."""
        path = os.path.join(INDEX_DIR, repo_name)
        os.makedirs(path, exist_ok=True)
        faiss.write_index(self.index, os.path.join(path, "index.faiss"))
        with open(os.path.join(path, "units.pkl"), "wb") as f:
            pickle.dump(self.units, f)
        print(f"[STORE] Saved index for '{repo_name}' ({self.index.ntotal} vectors)")

    def load(self, repo_name: str) -> bool:
        """Load a previously saved FAISS index. Returns True if successful."""
        path = os.path.join(INDEX_DIR, repo_name)
        index_path = os.path.join(path, "index.faiss")
        units_path = os.path.join(path, "units.pkl")
        if not os.path.exists(index_path) or not os.path.exists(units_path):
            return False
        self.index = faiss.read_index(index_path)
        with open(units_path, "rb") as f:
            self.units = pickle.load(f)
        print(f"[STORE] Loaded index for '{repo_name}' ({self.index.ntotal} vectors)")
        return True