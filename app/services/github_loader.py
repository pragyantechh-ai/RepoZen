import os
import subprocess
import shutil
from pathlib import Path
from app.core.config import UPLOAD_DIR


def clone_repo(github_url: str) -> str:
    """Clone a GitHub repo and return the local path.
    
    Supports:
      - https://github.com/owner/repo
      - https://github.com/owner/repo.git
    """
    # Extract repo name
    repo_name = github_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_path = os.path.join(UPLOAD_DIR, repo_name)

    if os.path.exists(clone_path):
        shutil.rmtree(clone_path)

    result = subprocess.run(
        ["git", "clone", "--depth", "1", github_url, clone_path],
        capture_output=True, text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr}")

    print(f"[GITHUB] Cloned {github_url} → {clone_path}")
    return clone_path


def get_repo_name(path: str) -> str:
    """Derive a clean repo name from a filesystem path."""
    return Path(path).name