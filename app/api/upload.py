import os
import zipfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.core.config import UPLOAD_DIR
from app.services.github_loader import clone_repo, get_repo_name
from app.rag.repo_indexer import index_repo
from app.rag.embeddings import embed_units
from app.rag.faiss_store import VectorStore

router = APIRouter()

# Global registry: repo_name → VectorStore
vector_stores: dict[str, VectorStore] = {}


class GitHubRequest(BaseModel):
    github_url: str


def _index_and_store(repo_path: str) -> str:
    """Run the full pipeline: index → embed → build vector store → persist."""
    repo_name = get_repo_name(repo_path)

    # 1. Extract code units
    units = index_repo(repo_path)
    if not units:
        raise HTTPException(status_code=400, detail="No indexable files found in repository.")

    # 2. Generate embeddings
    embeddings = embed_units(units)

    # 3. Build and save FAISS index
    store = VectorStore()
    store.build(embeddings, units)
    store.save(repo_name)

    # 4. Keep in memory for fast access
    vector_stores[repo_name] = store

    return repo_name


@router.post("/upload-zip")
async def upload_repo_zip(file: UploadFile = File(...)):
    """Upload a .zip of a repository, extract, index, and embed it."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Save zip
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Extract
    extract_path = file_path.replace(".zip", "")
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)

    # Clean up zip
    os.remove(file_path)

    # Run pipeline
    repo_name = _index_and_store(extract_path)

    return {
        "message": "Repository uploaded and indexed",
        "repo_name": repo_name,
        "path": extract_path,
    }


@router.post("/upload-github")
async def upload_repo_github(request: GitHubRequest):
    """Clone a GitHub repo by URL, index, and embed it."""
    try:
        repo_path = clone_repo(request.github_url)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

    repo_name = _index_and_store(repo_path)

    return {
        "message": "Repository cloned and indexed",
        "repo_name": repo_name,
        "path": repo_path,
    }


@router.get("/repos")
async def list_repos():
    """List all indexed repositories."""
    return {"repos": list(vector_stores.keys())}


def get_vector_store(repo_name: str) -> VectorStore:
    """Get a vector store by repo name, loading from disk if needed."""
    if repo_name in vector_stores:
        return vector_stores[repo_name]

    store = VectorStore()
    if store.load(repo_name):
        vector_stores[repo_name] = store
        return store

    raise HTTPException(status_code=404, detail=f"Repository '{repo_name}' not found. Upload it first.")