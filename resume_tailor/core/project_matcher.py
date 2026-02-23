"""Rank and select projects against a job posting."""

import json
from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import project_matching_prompt
from ..ai.schemas import MatchingResponse
from ..models.data_models import JobPosting, ProjectEntry


def match_projects(
    job: JobPosting,
    registry_projects: List[ProjectEntry],
    existing_projects_text: str,
    llm: LLMClient,
    console: Optional[Console] = None,
) -> MatchingResponse:
    """Send job + projects to LLM, return structured matching results."""
    if console:
        console.print("[dim]Matching projects to job requirements...[/dim]")

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
        }
        for p in registry_projects
    ]

    prompt = project_matching_prompt(
        json.dumps(job_dict, indent=2),
        json.dumps(projects_list, indent=2),
        existing_projects_text,
    )

    result = llm.generate_structured(prompt, MatchingResponse, temperature=0.4)

    if console:
        console.print(f"[dim]Selected {len(result.selected_projects)} projects:[/dim]")
        for p in result.selected_projects:
            console.print(f"  [dim]- {p.name} (score: {p.relevance_score:.2f})[/dim]")

    return result
