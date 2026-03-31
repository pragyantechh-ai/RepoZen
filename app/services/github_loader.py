import os
import stat
import shutil
from git import Repo
from app.core.config import UPLOAD_DIR


def _force_remove_readonly(func, path, excinfo):
    """Handle read-only files on Windows (e.g., .git/objects/pack/)."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


def clone_repo(repo_url: str) -> str:
    """
    Clone a git repository into UPLOAD_DIR.
    If the directory already exists, delete it first.

    Args:
        repo_url: Git clone URL

    Returns:
        Path to the cloned repository
    """
    # Extract repo name from URL
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    dest_path = os.path.join(UPLOAD_DIR, repo_name)

    # If already exists, force remove (handles read-only .git files on Windows)
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path, onerror=_force_remove_readonly)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    print(f"[GIT] Cloning {repo_url} → {dest_path}")
    Repo.clone_from(repo_url, dest_path)
    print(f"[GIT] Clone complete: {dest_path}")

    return dest_path