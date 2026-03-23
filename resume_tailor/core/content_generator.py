"""Generate tailored bullet points for selected projects."""

from pathlib import Path
from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import bullet_generation_prompt
from ..ai.schemas import BulletPointsResponse, SelectedProject
from ..models.data_models import JobPosting, ProjectEntry, TailoredProject
from ..utils.file_utils import short_project_display
from ..core.project_scanner import _read_readme, _read_all_source_files, _read_dependency_files, _build_dir_tree


def _find_registry_entry(name: str, registry: List[ProjectEntry]) -> Optional[ProjectEntry]:
    """Find a project entry by name from the registry (case-insensitive exact match)."""
    name_lower = name.strip().lower()
    for entry in registry:
        if entry.name.strip().lower() == name_lower:
            return entry
    return None


def _deep_scan_project(entry: ProjectEntry) -> str:
    """Read README, dir tree, dependency files, and source code from a project directory for rich context."""
    project_root = Path(entry.path).expanduser().resolve()
    if not project_root.is_dir():
        context = (
            f"Project: {entry.name}\n"
            f"Description: {entry.description}\n"
            f"Tech: {', '.join(entry.tech)}\n"
        )
        if entry.key_features:
            context += f"Key features: {' | '.join(entry.key_features)}\n"
        if entry.languages:
            context += f"Languages: {', '.join(entry.languages)}\n"
        return context

    readme   = _read_readme(project_root)
    tree     = _build_dir_tree(project_root)
    deps     = _read_dependency_files(project_root)
    sources  = _read_all_source_files(project_root)

    context = (
        f"Project: {entry.name}\n"
        f"Description: {entry.description}\n"
        f"Tech: {', '.join(entry.tech)}\n"
    )
    if entry.key_features:
        context += f"Key features: {' | '.join(entry.key_features)}\n"
    if entry.languages:
        context += f"Languages: {', '.join(entry.languages)}\n"
    context += (
        f"\nDirectory structure:\n{tree}\n\n"
        f"README:\n{readme}\n\n"
        f"Dependency / build files:\n{deps}\n\n"
        f"Source code:\n{sources}"
    )
    return context


def _get_project_context(
    name: str,
    registry: List[ProjectEntry],
    existing_projects: List[dict],
    console: Optional[Console] = None,
) -> tuple:
    """Get description, tech, and key_features for a selected project.

    For registry projects, deep-scans the directory.
    For existing resume projects, uses the resume content.
    Returns (description, tech_stack_str, key_features).
    """
    # Check registry (deep-scan the dir)
    entry = _find_registry_entry(name, registry)
    if entry:
        if console:
            console.print(f"    [dim]Deep-scanning {Path(entry.path).name}...[/dim]")
        deep_context = _deep_scan_project(entry)
        return deep_context, ", ".join(entry.tech), entry.key_features

    # Fall back to existing resume projects (case-insensitive exact match)
    name_lower = name.strip().lower()
    for p in existing_projects:
        if p["name"].strip().lower() == name_lower:
            desc = " ".join(p.get("bullets", []))
            return desc, p.get("tech_stack", ""), []

    if console:
        console.print(f"    [yellow]Warning: no context found for project '{name}' — bullets may be generic[/yellow]")
    return "", "", []


def generate_bullets(
    selected_projects: List[SelectedProject],
    job: JobPosting,
    registry: List[ProjectEntry],
    existing_projects: List[dict],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> List[TailoredProject]:
    """Generate tailored bullet points for each selected project.

    Deep-scans project directories for selected registry projects to get
    rich context before generating bullets.
    """
    if console:
        console.print("[dim]Generating tailored bullet points...[/dim]")

    job_tech = ", ".join(job.tech_stack)
    tailored = []

    for proj_info in selected_projects:
        name = proj_info.name
        angle = proj_info.suggested_angle

        if console:
            console.print(f"  [dim]Writing bullets for {short_project_display(name)}...[/dim]")

        desc, tech, key_features = _get_project_context(name, registry, existing_projects, console)

        prompt = bullet_generation_prompt(
            project_name=name,
            project_description=desc,
            project_tech=tech,
            job_title=job.title,
            job_tech=job_tech,
            suggested_angle=angle,
            key_features=key_features,
        )

        data = llm.generate_structured(prompt, BulletPointsResponse, temperature=0.5)

        tailored.append(TailoredProject(
            name=data.display_name or name,
            tech_stack_display=data.tech_stack_display or tech,
            bullet_points=data.bullet_points,
        ))

    return tailored
