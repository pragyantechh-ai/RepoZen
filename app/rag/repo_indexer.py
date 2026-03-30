import os
from typing import List, Dict
from pathlib import Path
from app.services.file_parser import CodeUnitExtractor
from app.services.chunking import chunk_units
from app.core.config import SUPPORTED_EXTENSIONS

# Directories / files to skip during indexing
SKIP_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    "env", ".tox", ".mypy_cache", ".pytest_cache", "dist",
    "build", ".egg-info", ".idea", ".vscode",
}

SKIP_FILES = {".DS_Store", "Thumbs.db"}


def index_repo(repo_path: str) -> List[Dict]:
    """Walk a repository, extract code units, chunk large ones, and return all units."""
    all_units: List[Dict] = []

    for root, dirs, files in os.walk(repo_path):
        # Prune directories we don't want to descend into
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if file in SKIP_FILES:
                continue

            ext = Path(file).suffix
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            file_path = os.path.join(root, file)

            # Make file_path relative to repo root for cleaner storage
            relative_path = os.path.relpath(file_path, repo_path)

            extractor = CodeUnitExtractor(file_path)
            units = extractor.extract()

            # Tag every unit with the relative path
            for u in units:
                u["relative_path"] = relative_path

            all_units.extend(units)

    # Chunk oversized units
    all_units = chunk_units(all_units)

    print(f"[INDEXER] Indexed {len(all_units)} units from {repo_path}")
    return all_units