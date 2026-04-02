from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── Upload / Analyze ─────────────────────────────────────────────────

class RepoUploadRequest(BaseModel):
    """Request body for uploading a repository via URL."""
    repo_url: Optional[str] = Field(
        None,
        description="Git clone URL. Either this or file upload must be provided.",
    )


class RepoUploadResponse(BaseModel):
    """Response after a repo is uploaded and queued for analysis."""
    session_id: str = Field(description="Unique session ID to use in chat")
    status: str = Field(description="Current status: analyzing, ready, error")
    message: str = Field(description="Human-readable status message")


class SessionStatusResponse(BaseModel):
    """Response for checking session/analysis status."""
    session_id: str
    status: str = Field(description="analyzing | ready | error")
    message: str
    repo_summary: Optional[Dict[str, Any]] = None


# ── Chat ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for a chat message."""
    session_id: str = Field(description="Session ID from the upload step")
    query: str = Field(description="User's natural language question or request")


class ChatResponse(BaseModel):
    """Full response from the agent pipeline."""
    session_id: str
    intent: str = Field(description="Classified intent: explanation, modification, debugging, testing, general")
    summary: str = Field(description="One-line summary of what was done")
    result: Dict[str, Any] = Field(description="Agent-specific output")
    validation: Optional[Dict[str, Any]] = Field(
        None,
        description="Validation result, if code was generated",
    )
    files_referenced: List[str] = Field(
        default_factory=list,
        description="Files used as context",
    )
    timing: Dict[str, float] = Field(
        default_factory=dict,
        description="Execution time per step",
    )