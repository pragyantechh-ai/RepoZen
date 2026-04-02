"""
Session Manager: Stores per-session state (PageIndex, Orchestrator, chat history).

In-memory implementation. Replace with Redis / DB for production.
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.services.chunking import PageIndex


@dataclass
class Session:
    """Represents one user session tied to an uploaded repository."""
    session_id: str
    status: str = "analyzing"           # analyzing | ready | error
    message: str = "Analyzing repository..."
    repo_path: Optional[str] = None
    page_index: Optional[PageIndex] = None
    orchestrator: Optional[object] = None  # Orchestrator (lazy import to avoid circular)
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    repo_summary: Optional[Dict] = None
    error: Optional[str] = None


class SessionManager:
    """Thread-safe in-memory session store."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        print(f"[SESSION_MANAGER] Initialized (id={id(self)})")

    def create_session(self) -> Session:
        """Create a new empty session and return it."""
        session_id = uuid.uuid4().hex[:12]
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        print(f"[SESSION_MANAGER] Created session {session_id} (total: {len(self._sessions)})")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID. Returns None if not found."""
        session = self._sessions.get(session_id)
        if session:
            print(f"[SESSION_MANAGER] Found session {session_id} (status={session.status})")
        else:
            print(
                f"[SESSION_MANAGER] Session {session_id} NOT FOUND. "
                f"Known sessions: {list(self._sessions.keys())}"
            )
        return session

    def mark_ready(
        self,
        session_id: str,
        page_index: PageIndex,
        repo_path: str,
    ) -> None:
        """Mark session as ready after analysis completes."""
        session = self._sessions.get(session_id)
        if not session:
            print(f"[SESSION_MANAGER] ❌ Cannot mark_ready: session {session_id} not found!")
            return

        # Lazy import to avoid circular dependency
        from app.agents.orch import Orchestrator

        session.page_index = page_index
        session.orchestrator = Orchestrator(page_index)
        session.repo_summary = page_index.get_summary()
        session.repo_path = repo_path
        session.status = "ready"
        session.message = "Repository analyzed and ready for questions."
        print(f"[SESSION_MANAGER] ✅ Session {session_id} marked READY")

    def mark_error(self, session_id: str, error: str) -> None:
        """Mark session as failed."""
        session = self._sessions.get(session_id)
        if not session:
            print(f"[SESSION_MANAGER] ❌ Cannot mark_error: session {session_id} not found!")
            return
        session.status = "error"
        session.message = f"Analysis failed: {error}"
        session.error = error
        print(f"[SESSION_MANAGER] ❌ Session {session_id} marked ERROR: {error}")

    def append_chat(self, session_id: str, role: str, content: str) -> None:
        """Append a message to the session's chat history."""
        session = self._sessions.get(session_id)
        if session:
            session.chat_history.append({"role": role, "content": content})

    def get_formatted_history(self, session_id: str, max_turns: int = 10) -> str:
        """Get chat history formatted as a string for the agents."""
        session = self._sessions.get(session_id)
        if not session or not session.chat_history:
            return ""

        recent = session.chat_history[-(max_turns * 2):]
        lines = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"{role}: {content}")

        return "\n".join(lines)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session. Returns True if it existed."""
        removed = self._sessions.pop(session_id, None) is not None
        print(f"[SESSION_MANAGER] Delete {session_id}: {'ok' if removed else 'not found'}")
        return removed


# Global singleton — imported by the API layer
session_manager = SessionManager()