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


_README_LIMIT        = 15_000  # max chars to read from README
_SOURCE_BUDGET_CHARS = 100_000  # global char budget across all source files
_SOURCE_PER_FILE_CHARS = 8_000
_SOURCE_PER_FILE_LINES = 300
_DEP_FILE_LIMIT      = 3_000   # max chars per dependency manifest

DEPENDENCY_FILES = [
    "requirements.txt", "pyproject.toml", "package.json",
    "go.mod", "Cargo.toml", "setup.py", "setup.cfg",
    "Pipfile", "pom.xml", "build.gradle",
]
_DEP_FILE_BLACKLIST = {"poetry.lock", "yarn.lock", "package-lock.json", "Pipfile.lock"}

_ENTRY_POINT_NAMES = {
    "main.py", "app.py", "server.py", "index.py", "run.py",
    "main.go", "main.rs", "main.js", "index.js", "server.js",
    "app.js", "index.ts", "app.ts", "server.ts", "main.ts",
    "Main.java", "Application.java", "main.c", "main.cpp",
}

_SKIP_DIRS = {"node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target", "vendor", ".git"}


def _read_readme(project_root: Path) -> str:
    """Read up to _README_LIMIT characters from the README file if it exists."""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme = project_root / name
        if readme.exists():
            try:
                with readme.open(encoding="utf-8", errors="ignore") as f:
                    content = f.read(_README_LIMIT + 1)
                if len(content) > _README_LIMIT:
                    content = content[:_README_LIMIT] + "\n... (truncated)"
                return content
            except Exception:
                pass
    return "(no README found)"


def _build_dir_tree(project_root: Path) -> str:
    """Build a directory tree string (up to 3 levels deep, max 300 entries)."""
    lines = [project_root.name + "/"]
    entry_count = 0

    def _walk(path: Path, prefix: str, depth: int) -> None:
        nonlocal entry_count
        if depth > 3 or entry_count >= 300:
            return
        try:
            children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return

        visible = [c for c in children if not c.name.startswith(".") and c.name not in _SKIP_DIRS]
        for i, child in enumerate(visible):
            if entry_count >= 300:
                lines.append(prefix + "└── ...")
                return
            connector = "└── " if i == len(visible) - 1 else "├── "
            lines.append(prefix + connector + child.name + ("/" if child.is_dir() else ""))
            entry_count += 1
            if child.is_dir():
                extension = "    " if i == len(visible) - 1 else "│   "
                _walk(child, prefix + extension, depth + 1)

    _walk(project_root, "", 1)
    return "\n".join(lines)


def _read_dependency_files(project_root: Path) -> str:
    """Read actual contents of dependency/build manifests at the project root."""
    sections = []
    for fname in DEPENDENCY_FILES:
        if fname in _DEP_FILE_BLACKLIST:
            continue
        fpath = project_root / fname
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8", errors="ignore")
                if len(content) > _DEP_FILE_LIMIT:
                    content = content[:_DEP_FILE_LIMIT] + "\n... (truncated)"
                sections.append(f"--- {fname} ---\n{content}")
            except Exception:
                pass
    return "\n\n".join(sections) if sections else "(no dependency files found)"


def _read_all_source_files(project_root: Path) -> str:
    """Read source files with a global char budget; entry-point files are read first."""
    priority: list[Path] = []
    rest: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in _SKIP_DIRS
        ]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fpath.suffix in SOURCE_EXTENSIONS:
                if fname in _ENTRY_POINT_NAMES:
                    priority.append(fpath)
                else:
                    rest.append(fpath)

    snippets = []
    total_chars = 0

    for fpath in priority + rest:
        if total_chars >= _SOURCE_BUDGET_CHARS:
            break
        try:
            raw = fpath.read_text(encoding="utf-8", errors="ignore")
            lines = raw.split("\n")[:_SOURCE_PER_FILE_LINES]
            chunk = "\n".join(lines)
            if len(chunk) > _SOURCE_PER_FILE_CHARS:
                chunk = chunk[:_SOURCE_PER_FILE_CHARS] + "\n... (truncated)"
            rel = fpath.relative_to(project_root)
            snippets.append(f"--- {rel} ---\n{chunk}")
            total_chars += len(chunk)
        except Exception:
            pass

    return "\n\n".join(snippets) if snippets else "(no source files found)"


def _sample_source_files(project_root: Path, max_files: int = 10, max_lines: int = 50) -> str:
    """Read first N lines of up to M source files. (Kept for backwards compatibility.)"""
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
                    lines = fpath.read_text(encoding="utf-8", errors="ignore").split("\n")[:max_lines]
                    rel = fpath.relative_to(project_root)
                    snippets.append(f"--- {rel} ---\n" + "\n".join(lines))
                    count += 1
                except Exception:
                    pass
        if count >= max_files:
            break

    return "\n\n".join(snippets) if snippets else "(no source files found)"


def _list_config_files(project_root: Path) -> str:
    """List config/build files present in the project root. (Kept for backwards compatibility.)"""
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
    readme  = _read_readme(project_root)
    tree    = _build_dir_tree(project_root)
    deps    = _read_dependency_files(project_root)
    sources = _read_all_source_files(project_root)

    prompt = project_summary_prompt(project_root.name, readme, tree, deps, sources)
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
    from ..utils.file_utils import short_project_display
    profiles = []
    for root in roots:
        if console:
            console.print(f"  [dim]Profiling {root.name}...[/dim]")
        try:
            profile = profile_project(root, llm)
            profiles.append(profile)
            if console:
                console.print(f"  [green]✓[/green] [dim]{short_project_display(profile.name, profile.description)}[/dim]")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            error_type = type(e).__name__
            if console:
                console.print(f"  [yellow]Skipped {root.name} ({error_type}): {e}[/yellow]")
            else:
                import sys
                print(f"  Skipped {root.name} ({error_type}): {e}", file=sys.stderr)

    return profiles
