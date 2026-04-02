"""
RepoZen API Routes — Session-based agent pipeline.

Endpoints:
  POST /api/upload/url      — Clone a GitHub repo and start analysis
  POST /api/upload/file     — Upload a .zip and start analysis
  GET  /api/status/{id}     — Poll analysis status
  POST /api/chat            — Ask a question (routes through agent pipeline)
  DELETE /api/session/{id}  — Cleanup session
"""

import os
import time
import zipfile
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from app.api.schemas import (
    RepoUploadRequest,
    RepoUploadResponse,
    SessionStatusResponse,
    ChatRequest,
    ChatResponse,
)
from app.api.session_manager import session_manager
from app.services.analysis_pipeline import analyze_repo_background
from app.core.config import UPLOAD_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


# ═════════════════════════════════════════════════════════════════════
# Step 1: Upload
# ═════════════════════════════════════════════════════════════════════

@router.post("/upload/url", response_model=RepoUploadResponse)
async def upload_repo_url(
    request: RepoUploadRequest,
    background_tasks: BackgroundTasks,
):
    """
    Clone a GitHub repo by URL and start background analysis.

    Returns a session_id to poll for status and use in chat.
    """
    if not request.repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required.")

    # Create a new session
    session = session_manager.create_session()

    # Kick off analysis in the background
    background_tasks.add_task(
        analyze_repo_background,
        session_id=session.session_id,
        repo_url=request.repo_url,
    )

    logger.info(
        f"[UPLOAD] Session {session.session_id} created for URL: {request.repo_url}"
    )

    return RepoUploadResponse(
        session_id=session.session_id,
        status=session.status,
        message="Repository upload received. Analysis in progress...",
    )


@router.post("/upload/file", response_model=RepoUploadResponse)
async def upload_repo_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a .zip of a repository, extract it, and start background analysis.

    Returns a session_id to poll for status and use in chat.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported.")

    # Save and extract
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    extract_path = file_path.replace(".zip", "")
    try:
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
    except zipfile.BadZipFile:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Invalid zip file.")

    # Clean up the zip
    os.remove(file_path)

    # Create session and start analysis
    session = session_manager.create_session()

    background_tasks.add_task(
        analyze_repo_background,
        session_id=session.session_id,
        uploaded_path=extract_path,
    )

    logger.info(
        f"[UPLOAD] Session {session.session_id} created for file: {file.filename}"
    )

    return RepoUploadResponse(
        session_id=session.session_id,
        status=session.status,
        message="Repository upload received. Analysis in progress...",
    )


# ═════════════════════════════════════════════════════════════════════
# Step 2: Poll Status
# ═════════════════════════════════════════════════════════════════════

@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_status(session_id: str):
    """
    Check the analysis status of a session.

    Poll this endpoint until status is 'ready' or 'error'.
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        message=session.message,
        repo_summary=session.repo_summary,
    )


# ═════════════════════════════════════════════════════════════════════
# Step 3 & 4: Chat (with automatic history)
# ═════════════════════════════════════════════════════════════════════

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question about an indexed repository.

    Routes through the full agent pipeline:
      Planner → Retriever → (Explainer | CodeGen | Debug | TestGen) → Validator

    Chat history is maintained automatically per session.
    """
    # ── Validate session ─────────────────────────────────────────────
    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{request.session_id}' not found.",
        )

    if session.status == "analyzing":
        raise HTTPException(
            status_code=409,
            detail="Repository is still being analyzed. Poll /api/status first.",
        )

    if session.status == "error":
        raise HTTPException(
            status_code=500,
            detail=f"Session is in error state: {session.error}",
        )

    if not session.orchestrator:
        raise HTTPException(
            status_code=500,
            detail="Session is ready but orchestrator is not initialized.",
        )

    # ── Get chat history ─────────────────────────────────────────────
    chat_history = session_manager.get_formatted_history(
        request.session_id, max_turns=10
    )

    # ── Record user message ──────────────────────────────────────────
    session_manager.append_chat(request.session_id, "user", request.query)

    # ── Run the agent pipeline ───────────────────────────────────────
    start_time = time.time()

    try:
        response = session.orchestrator.process(
            query=request.query,
            chat_history=chat_history,
        )
    except Exception as e:
        logger.error(f"[CHAT] Orchestrator error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent pipeline error: {str(e)}",
        )

    total_time = time.time() - start_time

    # ── Build timing info from agent trace ───────────────────────────
    timing = {"total": round(total_time, 2)}
    for step in response.get("agent_trace", []):
        agent_name = step.get("agent", "unknown")
        # We don't have per-step timing in the orchestrator yet,
        # so just mark them as present
        timing[agent_name] = 0.0
    timing["total"] = round(total_time, 2)

    # ── Extract summary for the response ─────────────────────────────
    plan = response.get("plan", {})
    result = response.get("result", {})
    intent = plan.get("intent", "unknown") if plan else "unknown"
    summary = plan.get("summary", "") if plan else ""

    # ── Build assistant response content for history ─────────────────
    assistant_content = _extract_response_content(result)
    session_manager.append_chat(
        request.session_id, "assistant", assistant_content
    )

    # ── Return ───────────────────────────────────────────────────────
    return ChatResponse(
        session_id=request.session_id,
        intent=intent,
        summary=summary,
        result=result,
        validation=response.get("validation"),
        files_referenced=response.get("files_referenced", []),
        timing=timing,
    )


# ═════════════════════════════════════════════════════════════════════
# Step 5: Cleanup
# ═════════════════════════════════════════════════════════════════════

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and free resources."""
    deleted = session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )
    return {"message": f"Session {session_id} deleted."}


# ═════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════

def _extract_response_content(result: dict) -> str:
    """
    Extract a text summary from the agent result for chat history.
    Keeps it short to avoid bloating context.
    """
    result_type = result.get("type", "")

    if result_type == "explanation":
        content = result.get("content", "")
        return content[:500] if len(content) > 500 else content

    elif result_type == "modification":
        changes = result.get("changes", [])
        summary = result.get("summary", "Code changes generated.")
        files = [c.get("file_path", "") for c in changes]
        return f"{summary} Files changed: {', '.join(files)}"

    elif result_type == "debugging":
        debug = result.get("debug", {})
        bugs = debug.get("bugs", [])
        assessment = debug.get("overall_assessment", "")
        return f"Found {len(bugs)} issues. {assessment[:300]}"

    elif result_type == "testing":
        test_files = result.get("test_files", [])
        summary = result.get("summary", "Tests generated.")
        return f"{summary} Generated {len(test_files)} test file(s)."

    elif result_type == "error":
        return result.get("content", "An error occurred.")

    return str(result)[:500]