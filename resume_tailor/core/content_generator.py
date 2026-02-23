"""Generate tailored bullet points for selected projects."""

from pathlib import Path
from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import bullet_generation_prompt
from ..ai.schemas import BulletPointsResponse, SelectedProject
from ..models.data_models import JobPosting, ProjectEntry, TailoredProject
from ..core.project_scanner import _read_readme, _sample_source_files, _list_config_files


def _find_registry_entry(name: str, registry: List[ProjectEntry]) -> Optional[ProjectEntry]:
    """Find a project entry by name from the registry."""
    for entry in registry:
        if entry.name.lower() == name.lower() or name.lower() in entry.name.lower():
            return entry
    return None


def _deep_scan_project(entry: ProjectEntry) -> str:
    """Read README + source snippets from a project directory for rich context."""
    project_root = Path(entry.path).expanduser().resolve()
    if not project_root.is_dir():
        return f"Project: {entry.name}\nDescription: {entry.description}\nTech: {', '.join(entry.tech)}"

    readme = _read_readme(project_root)
    sources = _sample_source_files(project_root)
    configs = _list_config_files(project_root)

    return (
        f"Project: {entry.name}\n"
        f"Description: {entry.description}\n"
        f"Tech: {', '.join(entry.tech)}\n\n"
        f"README:\n{readme}\n\n"
        f"Source snippets:\n{sources}\n\n"
        f"Config files: {configs}"
    )


def _get_project_context(
    name: str,
    registry: List[ProjectEntry],
    existing_projects: List[dict],
    console: Optional[Console] = None,
) -> tuple:
    """Get description and tech for a selected project.

    For registry projects, deep-scans the directory.
    For existing resume projects, uses the resume content.
    Returns (description, tech_stack_str).
    """
    # Check registry (deep-scan the dir)
    entry = _find_registry_entry(name, registry)
    if entry:
        if console:
            console.print(f"    [dim]Deep-scanning {Path(entry.path).name}...[/dim]")
        deep_context = _deep_scan_project(entry)
        return deep_context, ", ".join(entry.tech)

    # Fall back to existing resume projects
    for p in existing_projects:
        if p["name"].lower() == name.lower() or name.lower() in p["name"].lower():
            desc = " ".join(p.get("bullets", []))
            return desc, p.get("tech_stack", "")

    return "", ""


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
            console.print(f"  [dim]Writing bullets for {name}...[/dim]")

        desc, tech = _get_project_context(name, registry, existing_projects, console)

        prompt = bullet_generation_prompt(
            project_name=name,
            project_description=desc,
            project_tech=tech,
            job_title=job.title,
            job_tech=job_tech,
            suggested_angle=angle,
        )

        data = llm.generate_structured(prompt, BulletPointsResponse, temperature=0.5)

        tailored.append(TailoredProject(
            name=data.display_name or name,
            tech_stack_display=data.tech_stack_display or tech,
            bullet_points=data.bullet_points,
        ))

    return tailored
