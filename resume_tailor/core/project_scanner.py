"""Scan directories to discover and profile software projects."""

import os
from pathlib import Path
from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import project_summary_prompt
from ..ai.schemas import ProjectProfileResponse
from ..models.data_models import ProjectProfile

# Markers that indicate a project root
PROJECT_MARKERS = [
    "README.md", "README.rst", "README.txt", "README",
    "Makefile", "CMakeLists.txt",
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "docker-compose.yml", "Dockerfile",
]

# Source file extensions to sample
SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go",
    ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
}

# Config/build files to note
CONFIG_FILES = {
    "Makefile", "CMakeLists.txt", "Dockerfile", "docker-compose.yml",
    "package.json", "pyproject.toml", "setup.py", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle", ".env.example",
    "tsconfig.json", "webpack.config.js", "requirements.txt",
}


def find_project_roots(scan_dirs: List[str]) -> List[Path]:
    """Walk scan directories and find directories containing project markers."""
    roots = []
    seen = set()

    for scan_dir in scan_dirs:
        base = Path(scan_dir).expanduser().resolve()
        if not base.is_dir():
            continue

        for dirpath, dirnames, filenames in os.walk(base):
            # Check for .git before filtering (hidden-dir filter removes it)
            has_git = ".git" in dirnames or ".git" in filenames

            # Skip hidden dirs and common non-project dirs
            dirnames[:] = [
                d for d in dirnames
                if not d.startswith(".")
                and d not in {"node_modules", "__pycache__", "venv", ".venv", "dist", "build", "site-packages", "share"}
            ]

            # Skip Python venvs with non-standard names
            if "pyvenv.cfg" in filenames:
                dirnames.clear()
                continue

            path = Path(dirpath)
            has_marker = has_git or any(marker in filenames or marker in dirnames for marker in PROJECT_MARKERS)
            if has_marker and str(path) not in seen:
                seen.add(str(path))
                roots.append(path)
                dirnames.clear()

    return roots


def _read_readme(project_root: Path) -> str:
    """Read the README file if it exists."""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = project_root / name
        if readme.exists():
            try:
                content = readme.read_text(errors="ignore")
                # Truncate very long READMEs
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"
                return content
            except Exception:
                pass
    return "(no README found)"


def _sample_source_files(project_root: Path, max_files: int = 10, max_lines: int = 50) -> str:
    """Read first N lines of up to M source files."""
    snippets = []
    count = 0

    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in {"node_modules", "__pycache__", "venv"}]

        for fname in filenames:
            if count >= max_files:
                break
            fpath = Path(dirpath) / fname
            if fpath.suffix in SOURCE_EXTENSIONS:
                try:
                    lines = fpath.read_text(errors="ignore").split("\n")[:max_lines]
                    rel = fpath.relative_to(project_root)
                    snippets.append(f"--- {rel} ---\n" + "\n".join(lines))
                    count += 1
                except Exception:
                    pass
        if count >= max_files:
            break

    return "\n\n".join(snippets) if snippets else "(no source files found)"


def _list_config_files(project_root: Path) -> str:
    """List config/build files present in the project root."""
    found = []
    for name in sorted(CONFIG_FILES):
        if (project_root / name).exists():
            found.append(name)
    return ", ".join(found) if found else "(none)"


def profile_project(
    project_root: Path,
    llm: LLMClient,
) -> ProjectProfile:
    """Use LLM to summarize a single project into a ProjectProfile."""
    readme = _read_readme(project_root)
    sources = _sample_source_files(project_root)
    configs = _list_config_files(project_root)

    prompt = project_summary_prompt(project_root.name, readme, sources, configs)
    data = llm.generate_structured(prompt, ProjectProfileResponse, temperature=0.3)

    return ProjectProfile(
        name=data.name or project_root.name,
        path=str(project_root),
        description=data.description,
        tech_stack=data.tech_stack,
        key_features=data.key_features,
        languages=data.languages,
    )


def profile_projects(
    roots: List[Path],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> List[ProjectProfile]:
    """Profile a list of project roots with LLM."""
    profiles = []
    for root in roots:
        if console:
            console.print(f"  [dim]Profiling {root.name}...[/dim]")
        try:
            profile = profile_project(root, llm)
            profiles.append(profile)
        except Exception as e:
            if console:
                console.print(f"  [yellow]Skipped {root.name}: {e}[/yellow]")

    return profiles
