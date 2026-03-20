"""Generate a LinkedIn recruiter connect message from pipeline data."""

from typing import Optional

from rich.console import Console

from ..ai.prompts import linkedin_message_prompt
from ..ai.schemas import LinkedInMessageResponse, MatchingResponse
from ..models.data_models import JobPosting, TailoredResume


def generate_linkedin_message(
    job: JobPosting,
    tailored: TailoredResume,
    match_result: MatchingResponse,
    llm,
    recruiter_name: Optional[str] = None,
    graduation: Optional[str] = None,
    console: Optional[Console] = None,
    limit: int = 300,
) -> str:
    if not tailored.projects:
        if console:
            console.print("[yellow]LinkedIn: No tailored projects found — skipping message generation.[/yellow]")
        return ""

    top_project = tailored.projects[0]
    prompt = linkedin_message_prompt(
        job_title=job.title,
        company=job.company,
        tech_stack=job.tech_stack[:10],
        top_project_name=top_project.name,
        top_project_bullets=top_project.bullet_points,
        professional_summary=match_result.professional_summary,
        recruiter_name_or_placeholder=recruiter_name or "[Recruiter Name]",
        graduation_or_placeholder=graduation or "May 2026",
        limit=limit,
    )

    response = llm.generate_structured(prompt, LinkedInMessageResponse, temperature=0.8)
    msg = response.message
    if len(msg) > limit:
        msg = msg[:limit - 3] + "..."
    return msg
