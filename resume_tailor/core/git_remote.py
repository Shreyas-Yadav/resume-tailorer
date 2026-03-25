"""Helpers for reading git remote metadata from project directories."""

import subprocess
from pathlib import Path
from typing import Optional


def get_git_remote_url(project_path: str) -> Optional[str]:
    """Return the best remote URL for a git repo, preferring origin then upstream."""
    path = Path(project_path).expanduser()
    if not path.is_dir():
        return None

    for remote_name in ("origin", "upstream"):
        url = _get_named_remote(path, remote_name)
        if url:
            return url

    return _get_first_fetch_remote(path)


def _get_named_remote(path: Path, remote_name: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", remote_name],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    url = result.stdout.strip()
    return url or None


def _get_first_fetch_remote(path: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "remote", "-v"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "(fetch)":
            return parts[1]
    return None
