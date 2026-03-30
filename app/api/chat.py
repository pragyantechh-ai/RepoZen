import os
import requests

from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.retrieval import retrieve
from app.api.upload import get_vector_store
from app.core.config import OPENROUTER_API_KEY, OPENROUTER_MODEL

router = APIRouter()


class ChatRequest(BaseModel):
    repo_name: str
    query: str


@router.post("/ask")
async def chat(request: ChatRequest):
    """Ask a question about an indexed repository."""
    store = get_vector_store(request.repo_name)

    # Retrieve relevant code units
    docs = retrieve(request.query, store, top_k=5)

    # Build context from retrieved units
    context_parts = []
    for d in docs:
        header = f"# {d['type']} {d['name']} — {d.get('relative_path', d['file_path'])}"
        context_parts.append(f"{header}\n```\n{d['content']}\n```")

    context = "\n\n".join(context_parts)

    prompt = f"""You are RepoZen, an expert AI code assistant. 
You answer questions about a codebase using the retrieved code context below.
Be specific, reference file paths, function/class names, and line numbers when possible.

## Retrieved Code Context:
{context}

## User Question:
{request.query}

## Answer:"""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are RepoZen, an AI code assistant that explains codebases."},
                {"role": "user", "content": prompt},
            ],
        },
    )

    if response.status_code != 200:
        return {"error": f"LLM request failed: {response.text}"}

    data = response.json()
    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "No response.")

    return {
        "answer": answer,
        "sources": [
            {
                "name": d["name"],
                "type": d["type"],
                "file": d.get("relative_path", d["file_path"]),
                "lines": f"{d['start_line']}-{d['end_line']}",
                "score": d.get("score"),
            }
            for d in docs
        ],
    }