"""
Analysis Pipeline: Clones, parses, chunks, and indexes a repository.

Runs as a FastAPI background task so the upload endpoint returns immediately.
"""

import traceback
from typing import Optional

from app.services.github_loader import clone_repo
from app.services.file_parser import PageIndexBuilder
from app.services.chunking import PageIndex
from app.core.config import UPLOAD_DIR


def analyze_repo_background(
    session_id: str,
    repo_url: Optional[str] = None,
    uploaded_path: Optional[str] = None,
) -> None:
    """
    Background task: clone/extract → parse → chunk → index.

    Imports session_manager INSIDE the function to guarantee
    we get the same singleton instance as the API layer.
    """
    # Late import to avoid circular imports AND ensure same singleton
    from app.api.session_manager import session_manager

    try:
        # ── Step 1: Get repo on disk ─────────────────────────────────
        if repo_url:
            print(f"[PIPELINE] Cloning {repo_url} ...")
            repo_path = clone_repo(repo_url)
        elif uploaded_path:
            repo_path = uploaded_path
        else:
            raise ValueError("Either repo_url or uploaded_path must be provided")

        print(f"[PIPELINE] Repo at: {repo_path}")

        # ── Step 2: Parse and index files ────────────────────────────
        print("[PIPELINE] Parsing and indexing files...")
        builder = PageIndexBuilder(repo_path)
        pages = builder.build()
        print(f"[PIPELINE] Created {len(pages)} pages")

        if not pages:
            raise ValueError("No parseable files found in repository")

        # ── Step 3: Build page index ─────────────────────────────────
        print("[PIPELINE] Building page index...")
        page_index = PageIndex(pages)

        summary = page_index.get_summary()
        print(
            f"[PIPELINE] Index ready: "
            f"{summary.get('total_pages', 0)} pages, "
            f"{len(summary.get('files', []))} files, "
            f"languages: {summary.get('languages', [])}"
        )

        # ── Step 4: Mark session ready ───────────────────────────────
        print(f"[PIPELINE] Initializing orchestrator for session {session_id}...")
        session_manager.mark_ready(
            session_id=session_id,
            page_index=page_index,
            repo_path=repo_path,
        )
        print(f"[PIPELINE] ✅ Session {session_id} is READY")

    except Exception as e:
        print(f"[PIPELINE] ❌ ERROR: {e}")
        traceback.print_exc()
        # Late import here too
        from app.api.session_manager import session_manager as sm
        sm.mark_error(session_id, str(e))