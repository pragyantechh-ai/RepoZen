from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np
from app.core.config import EMBEDDING_MODEL_NAME

model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed_units(units: List[Dict]) -> np.ndarray:
    """Generate embeddings for a list of code units."""
    texts = []
    for u in units:
        # Build a rich text representation for embedding
        parts = [f"{u['type']} {u['name']}"]
        if u.get("parent"):
            parts.append(f"in class {u['parent']}")
        if u.get("relative_path"):
            parts.append(f"file: {u['relative_path']}")
        if u.get("docstring"):
            parts.append(f"docstring: {u['docstring']}")
        parts.append(u.get("content", ""))
        texts.append("\n".join(parts))

    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    return np.array(embeddings, dtype="float32")