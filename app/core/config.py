import os
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "repos"
INDEX_DIR = BASE_DIR / "indexes"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# LLM
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")

# Embedding
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# RAG
DEFAULT_TOP_K = 5

# Supported file extensions for indexing
SUPPORTED_EXTENSIONS = [
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".java", ".go", ".rs", ".rb", ".cpp", ".c", ".h",
    ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
]