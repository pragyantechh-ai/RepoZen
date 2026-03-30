from typing import List, Dict
import uuid


# Maximum characters per chunk (roughly ~500 tokens for MiniLM)
MAX_CHUNK_SIZE = 1500
OVERLAP = 200


def chunk_units(units: List[Dict]) -> List[Dict]:
    """Split oversized code units into smaller overlapping chunks.
    Small units pass through unchanged.
    """
    chunked = []

    for unit in units:
        content = unit.get("content", "") or ""

        if len(content) <= MAX_CHUNK_SIZE:
            chunked.append(unit)
            continue

        # Split into overlapping chunks
        start = 0
        chunk_idx = 0
        while start < len(content):
            end = start + MAX_CHUNK_SIZE
            chunk_text = content[start:end]

            chunked.append({
                **unit,
                "id": str(uuid.uuid4()),
                "content": chunk_text,
                "name": f"{unit['name']}_chunk_{chunk_idx}",
                "chunk_index": chunk_idx,
                "original_unit_id": unit["id"],
            })

            start += MAX_CHUNK_SIZE - OVERLAP
            chunk_idx += 1

    return chunked