"""Review and validate tailored resume content."""

import json
import math
import re
from typing import Iterable, List, Optional

from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import resume_review_prompt
from ..ai.schemas import ResumeReviewResponse
from ..models.data_models import JobPosting, ResumeReview, ReviewIssue, TailoredResume

_GENERIC_BOLD_TERMS = {
    "api",
    "apis",
    "architecture",
    "optimization",
    "performance",
    "reliability",
    "testing",
    "security",
    "automation",
    "observability",
    "scalability",
}

_UNDERFILL_LINE_THRESHOLD = 43


def validate_project_bullets(
    bullet_points: List[str],
    supported_terms: Iterable[str],
    explicit_metrics: Iterable[str],
    strict_truthfulness: bool = True,
) -> List[str]:
    """Return unsupported claim messages for a set of project bullets."""
    issues: List[str] = []
    supported = {term.strip().lower() for term in supported_terms if term.strip()}
    explicit_metric_text = " ".join(explicit_metrics).lower()

    for bullet in bullet_points:
        for match in re.findall(r"\*\*(.+?)\*\*", bullet):
            term = match.strip().lower().rstrip(":")
            if term in _GENERIC_BOLD_TERMS:
                continue
            if term not in supported and not any(term in item or item in term for item in supported):
                issues.append(f"Unsupported emphasized term in bullet: {match}")

        if strict_truthfulness and re.search(r"\d", bullet):
            metrics = re.findall(r"\d+(?:\.\d+)?%?|\d+\+?", bullet)
            for metric in metrics:
                if metric.lower() not in explicit_metric_text:
                    issues.append(f"Unsupported metric in bullet: {bullet}")
                    break

    return issues


def estimate_resume_lines(tailored: TailoredResume) -> int:
    """Roughly estimate rendered line usage for one-page resume density checks."""
    lines = 5  # heading/contact block
    lines += max(2, math.ceil(len(tailored.professional_summary) / 110)) + 1

    if tailored.experience:
        lines += 1
    for entry in tailored.experience:
        lines += 2
        for bullet in entry.bullet_points:
            lines += max(1, math.ceil(len(bullet) / 105))

    if tailored.projects:
        lines += 1
    for project in tailored.projects:
        lines += max(1, math.ceil(len(project.name + " " + project.tech_stack_display) / 90))
        for bullet in project.bullet_points:
            lines += max(1, math.ceil(len(bullet) / 105))

    lines += 3  # education section

    skill_lines = 0
    if tailored.skills.languages:
        skill_lines += max(1, math.ceil(len(", ".join(tailored.skills.languages)) / 95))
    if tailored.skills.infrastructure_and_tools:
        skill_lines += max(1, math.ceil(len(", ".join(tailored.skills.infrastructure_and_tools)) / 95))
    if tailored.skills.coursework:
        skill_lines += max(1, math.ceil(len(", ".join(tailored.skills.coursework)) / 95))
    lines += 1 + skill_lines

    return lines


def recommend_page_fill_actions(tailored: TailoredResume) -> List[str]:
    """Return human-readable page-fill recommendations based on current density."""
    recommendations: List[str] = []

    sparse_experience = [entry for entry in tailored.experience if len(entry.bullet_points) < 3]
    if sparse_experience:
        recommendations.append("Add a third bullet to the strongest experience entry.")

    if len(tailored.projects) < 4:
        recommendations.append("Add one more project if it covers a missing requirement theme.")

    if tailored.projects and all(len(project.bullet_points) <= 3 for project in tailored.projects):
        recommendations.append("Add one more distinct bullet to the strongest project.")

    if len(tailored.skills.coursework) < 2 or len(tailored.skills.infrastructure_and_tools) < 10:
        recommendations.append("Restore one or two relevant skills or coursework items.")

    if len(tailored.professional_summary) < 220:
        recommendations.append("Slightly expand the professional summary with one more targeted sentence.")

    return recommendations


def review_resume(
    job: JobPosting,
    tailored: TailoredResume,
    llm: LLMClient,
    console: Optional[Console] = None,
) -> ResumeReview:
    """Review the assembled resume draft for gaps and quality issues."""
    if console:
        console.print("[dim]Reviewing tailored resume quality...[/dim]")

    prompt = resume_review_prompt(
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
        resume_json=json.dumps(
            {
                "professional_summary": tailored.professional_summary,
                "projects": [
                    {
                        "name": project.name,
                        "tech_stack_display": project.tech_stack_display,
                        "bullet_points": project.bullet_points,
                    }
                    for project in tailored.projects
                ],
                "experience": [
                    {
                        "company": entry.company,
                        "role": entry.role,
                        "bullet_points": entry.bullet_points,
                    }
                    for entry in tailored.experience
                ],
                "skills": {
                    "languages": tailored.skills.languages,
                    "infrastructure_and_tools": tailored.skills.infrastructure_and_tools,
                    "coursework": tailored.skills.coursework,
                },
            },
            indent=2,
        ),
    )
    response = llm.generate_structured(prompt, ResumeReviewResponse, temperature=0.2)
    estimated_lines = estimate_resume_lines(tailored)
    heuristic_underfilled = estimated_lines < _UNDERFILL_LINE_THRESHOLD
    page_fill_recommendations = list(dict.fromkeys(response.page_fill_recommendations + recommend_page_fill_actions(tailored)))
    return ResumeReview(
        passed=response.passed,
        underfilled=response.underfilled or heuristic_underfilled,
        missing_requirements=response.missing_requirements,
        duplicated_themes=response.duplicated_themes,
        unsupported_claims=response.unsupported_claims,
        trim_suggestions=response.trim_suggestions,
        page_fill_recommendations=page_fill_recommendations,
        issues=[ReviewIssue(severity=issue.severity, message=issue.message) for issue in response.issues],
    )
