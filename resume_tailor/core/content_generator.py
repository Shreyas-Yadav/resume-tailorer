"""Generate tailored bullet points for selected projects."""

from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import bullet_generation_prompt
from ..ai.schemas import BulletPointsResponse, SelectedProject
from ..models.data_models import EnrichedProject, JobPosting, TailoredProject
from ..utils.file_utils import short_project_display


def _find_registry_entry(name: str, registry: List[EnrichedProject]) -> Optional[EnrichedProject]:
    """Find an enriched project entry by name from the registry (case-insensitive exact match)."""
    name_lower = name.strip().lower()
    for entry in registry:
        if entry.name.strip().lower() == name_lower:
            return entry
    return None


def _get_project_context(
    name: str,
    registry: List[EnrichedProject],
    console: Optional[Console] = None,
) -> tuple:
    """Get evidence summary, tech stack string, key features, and explicit metrics for a selected project."""
    entry = _find_registry_entry(name, registry)
    if entry:
        if console:
            console.print(f"    [dim]Using enriched evidence for {entry.name}...[/dim]")
        description = "\n".join(
            [
                f"Description: {entry.description}",
                f"Evidence summary: {entry.evidence_summary}",
                f"Architecture: {' | '.join(entry.architecture_signals)}",
                f"Outcomes: {' | '.join(entry.outcomes)}",
                f"Explicit metrics: {' | '.join(entry.explicit_metrics)}",
            ]
        )
        return description, ", ".join(entry.tech), entry.key_features, entry.explicit_metrics

    if console:
        console.print(f"    [yellow]Warning: no context found for project '{name}' — bullets may be generic[/yellow]")
    return "", "", [], []


def generate_bullets(
    selected_projects: List[SelectedProject],
    job: JobPosting,
    registry: List[EnrichedProject],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> List[tuple[TailoredProject, List[str], str]]:
    """Generate tailored bullet points for each selected project.

    Uses enriched project evidence to generate bullets.
    """
    if console:
        console.print("[dim]Generating tailored bullet points...[/dim]")

    job_tech = ", ".join(job.tech_stack)
    tailored: List[tuple[TailoredProject, List[str], str]] = []

    for proj_info in selected_projects:
        name = proj_info.name
        angle = proj_info.suggested_angle

        if console:
            console.print(f"  [dim]Writing bullets for {short_project_display(name)}...[/dim]")

        desc, tech, key_features, explicit_metrics = _get_project_context(name, registry, console)

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

        tailored.append((
            TailoredProject(
                name=data.display_name or name,
                tech_stack_display=data.tech_stack_display or tech,
                bullet_points=data.bullet_points,
            ),
            explicit_metrics,
            name,
        ))

    return tailored
