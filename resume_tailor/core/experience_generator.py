"""Tailor experience bullets for a target role."""

import json
from typing import List, Optional

from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import (
    additional_experience_bullet_prompt,
    experience_repair_prompt,
    experience_tailoring_prompt,
    summary_rewrite_prompt,
)
from ..ai.schemas import (
    AdditionalBulletResponse,
    ExperienceRepairResponse,
    ExperienceTailoringResponse,
    SummaryRewriteResponse,
)
from ..models.data_models import ExistingExperienceEntry, JobPosting, TailoredExperienceEntry


def tailor_experience(
    job: JobPosting,
    experience: List[ExistingExperienceEntry],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> List[TailoredExperienceEntry]:
    """Rewrite experience bullets while preserving role/company pairing."""
    if not experience:
        return []

    if console:
        console.print("[dim]Tailoring experience bullets...[/dim]")

    prompt = experience_tailoring_prompt(
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
        experience_json=json.dumps(
            [
                {
                    "company": entry.company,
                    "role": entry.role,
                    "bullet_points": entry.bullets,
                }
                for entry in experience
            ],
            indent=2,
        ),
    )

    response = llm.generate_structured(prompt, ExperienceTailoringResponse, temperature=0.4)
    return [
        TailoredExperienceEntry(
            company=entry.company,
            role=entry.role,
            bullet_points=entry.bullet_points,
        )
        for entry in response.entries
    ]


def add_experience_bullet(
    job: JobPosting,
    source_entry: ExistingExperienceEntry,
    tailored_entry: TailoredExperienceEntry,
    llm: LLMClient,
    console: Optional[Console] = None,
) -> str:
    """Generate one additional targeted bullet for an existing experience entry."""
    if console:
        console.print(f"  [dim]Expanding experience for {tailored_entry.role} at {tailored_entry.company}...[/dim]")

    prompt = additional_experience_bullet_prompt(
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
        experience_entry_json=json.dumps(
            {
                "company": source_entry.company,
                "role": source_entry.role,
                "source_bullets": source_entry.bullets,
                "current_tailored_bullets": tailored_entry.bullet_points,
            },
            indent=2,
        ),
    )
    response = llm.generate_structured(prompt, AdditionalBulletResponse, temperature=0.4)
    return response.bullet_point


def repair_experience_framing(
    job: JobPosting,
    tailored_experience: List[TailoredExperienceEntry],
    llm: LLMClient,
    console: Optional[Console] = None,
) -> List[TailoredExperienceEntry]:
    """Reframe weak experience entries to sound more technically credible."""
    if not tailored_experience:
        return tailored_experience

    if console:
        console.print("[dim]Repairing experience framing...[/dim]")

    prompt = experience_repair_prompt(
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
        experience_json=json.dumps(
            [
                {
                    "company": entry.company,
                    "role": entry.role,
                    "bullet_points": entry.bullet_points,
                }
                for entry in tailored_experience
            ],
            indent=2,
        ),
    )
    response = llm.generate_structured(prompt, ExperienceRepairResponse, temperature=0.35)
    return [
        TailoredExperienceEntry(company=entry.company, role=entry.role, bullet_points=entry.bullet_points)
        for entry in response.entries
    ]


def rewrite_summary(
    job: JobPosting,
    projects: list,
    experience: List[TailoredExperienceEntry],
    current_summary: str,
    llm: LLMClient,
    console: Optional[Console] = None,
) -> str:
    """Rewrite a weak summary using selected projects and experience as evidence."""
    if console:
        console.print("[dim]Rewriting professional summary...[/dim]")

    prompt = summary_rewrite_prompt(
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
        projects_json=json.dumps(projects, indent=2),
        experience_json=json.dumps(
            [
                {
                    "company": entry.company,
                    "role": entry.role,
                    "bullet_points": entry.bullet_points,
                }
                for entry in experience
            ],
            indent=2,
        ),
        current_summary=current_summary,
    )
    response = llm.generate_structured(prompt, SummaryRewriteResponse, temperature=0.35)
    return response.professional_summary
