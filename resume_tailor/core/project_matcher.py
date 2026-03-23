"""Rank and select projects against a job posting."""

import json
from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..utils.file_utils import short_project_display
from ..ai.prompts import project_matching_prompt
from ..ai.schemas import MatchingResponse
from ..models.data_models import JobPosting, ProjectEntry


def _dedupe_registry_projects(
    registry_projects: List[ProjectEntry],
    console: Optional[Console] = None,
) -> List[ProjectEntry]:
    """Keep the first registry entry for each normalized project name."""
    deduped: dict[str, ProjectEntry] = {}
    duplicate_count = 0

    for project in registry_projects:
        key = project.name.strip().lower()
        if key in deduped:
            duplicate_count += 1
            continue
        deduped[key] = project

    if duplicate_count and console:
        console.print(f"[yellow]Warning: removed {duplicate_count} duplicate project registry entr(y/ies) before matching[/yellow]")

    return list(deduped.values())


def match_projects(
    job: JobPosting,
    registry_projects: List[ProjectEntry],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> MatchingResponse:
    """Send job + registry projects to LLM, return structured matching results."""
    if console:
        console.print("[dim]Matching projects to job requirements...[/dim]")

    registry_projects = _dedupe_registry_projects(registry_projects, console)

    job_dict = {
        "title": job.title,
        "company": job.company,
        "responsibilities": job.responsibilities,
        "required_qualifications": job.required_qualifications,
        "preferred_qualifications": job.preferred_qualifications,
        "tech_stack": job.tech_stack,
    }

    projects_list = [
        {
            "name": p.name,
            "description": p.description,
            "tech": p.tech,
            "key_features": p.key_features,
            "languages": p.languages,
        }
        for p in registry_projects
    ]

    prompt = project_matching_prompt(
        json.dumps(job_dict, indent=2),
        json.dumps(projects_list, indent=2),
    )

    result = llm.generate_structured(prompt, MatchingResponse, temperature=0.4)

    # Programmatic deduplication — keep highest-scoring entry per unique name
    seen: dict = {}
    for p in result.selected_projects:
        key = p.name.strip().lower()
        if key not in seen or p.relevance_score > seen[key].relevance_score:
            seen[key] = p
    deduped = list(seen.values())
    if len(deduped) < len(result.selected_projects) and console:
        console.print(f"[yellow]Warning: removed {len(result.selected_projects) - len(deduped)} duplicate project(s)[/yellow]")
    result.selected_projects = deduped

    # Validate: drop any project the LLM hallucinated (not in registry)
    valid_names = {p.name.strip().lower() for p in registry_projects}

    def _is_valid(name: str) -> bool:
        n = name.strip().lower()
        return any(n in v or v in n for v in valid_names)

    before = len(result.selected_projects)
    result.selected_projects = [p for p in result.selected_projects if _is_valid(p.name)]
    if len(result.selected_projects) < before and console:
        removed = before - len(result.selected_projects)
        console.print(f"[yellow]Warning: removed {removed} hallucinated project(s) not found in registry[/yellow]")

    if console:
        console.print(f"[dim]Selected {len(result.selected_projects)} projects:[/dim]")
        for p in result.selected_projects:
            console.print(f"  [dim]- {short_project_display(p.name)} (score: {p.relevance_score:.2f})[/dim]")

    return result
