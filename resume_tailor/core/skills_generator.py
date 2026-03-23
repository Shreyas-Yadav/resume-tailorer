"""Tailor technical skills section for a target role."""

import json
from typing import Iterable, Optional

from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import skills_tailoring_prompt
from ..ai.schemas import SkillsTailoringResponse
from ..models.data_models import ExistingSkills, JobPosting, TailoredSkills


def tailor_skills(
    job: JobPosting,
    existing_skills: ExistingSkills,
    project_skill_inventory: Iterable[str],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> TailoredSkills:
    """Curate a targeted skills section."""
    if console:
        console.print("[dim]Tailoring skills section...[/dim]")

    prompt = skills_tailoring_prompt(
        job_posting_json=json.dumps(
            {
                "title": job.title,
                "company": job.company,
                "responsibilities": job.responsibilities,
                "required_qualifications": job.required_qualifications,
                "preferred_qualifications": job.preferred_qualifications,
                "tech_stack": job.tech_stack,
            },
            indent=2,
        ),
        skills_json=json.dumps(
            {
                "languages": existing_skills.languages,
                "infrastructure_and_tools": existing_skills.infrastructure_and_tools,
                "coursework": existing_skills.coursework,
            },
            indent=2,
        ),
        available_project_skills=", ".join(sorted({skill for skill in project_skill_inventory if skill})),
    )
    response = llm.generate_structured(prompt, SkillsTailoringResponse, temperature=0.3)
    return TailoredSkills(
        languages=response.languages,
        infrastructure_and_tools=response.infrastructure_and_tools,
        coursework=response.coursework,
    )
