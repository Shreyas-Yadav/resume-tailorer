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
_GENERIC_SUMMARY_PHRASES = {
    "passionate",
    "enthusiastic",
    "eager to contribute",
    "team player",
    "highly motivated",
    "passion for",
}
_AI_DEPTH_TERMS = {
    "workflow",
    "orchestration",
    "tool calling",
    "tool-call",
    "retrieval",
    "background jobs",
    "queue",
    "pipeline",
    "automation",
    "agent",
}


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


def _has_generic_summary(summary: str) -> bool:
    lowered = summary.lower()
    return any(phrase in lowered for phrase in _GENERIC_SUMMARY_PHRASES)


def _has_shallow_ai_positioning(job: JobPosting, tailored: TailoredResume) -> bool:
    job_text = " ".join(job.responsibilities + job.required_qualifications + job.preferred_qualifications + job.tech_stack).lower()
    if not any(term in job_text for term in {"agent", "llm", "workflow", "automation", "ai"}):
        return False

    resume_text = " ".join(
        [tailored.professional_summary]
        + [bullet for project in tailored.projects for bullet in project.bullet_points]
    ).lower()
    mentions_ai = any(term in resume_text for term in {"llm", "openai", "langchain", "hugging face", "agent", "ai"})
    has_depth = any(term in resume_text for term in _AI_DEPTH_TERMS)
    return mentions_ai and not has_depth


def _has_weak_experience_framing(job: JobPosting, tailored: TailoredResume) -> bool:
    job_text = " ".join(job.responsibilities + job.required_qualifications + job.preferred_qualifications).lower()
    if not tailored.experience:
        return True
    experience_text = " ".join(
        [entry.role for entry in tailored.experience] + [bullet for entry in tailored.experience for bullet in entry.bullet_points]
    ).lower()
    technical_markers = {"api", "system", "debug", "linux", "backend", "automation", "testing", "service", "database"}
    if not any(marker in experience_text for marker in technical_markers):
        return True
    if "software engineer" in job_text and "teaching assistant" in experience_text and "debug" not in experience_text:
        return True
    return False


def _credibility_gaps(tailored: TailoredResume) -> List[str]:
    gaps: List[str] = []
    if tailored.projects and not any(project.repo_url or project.demo_url for project in tailored.projects):
        gaps.append("Selected projects do not include repo or demo links for credibility.")
    if any(("microservice" in bullet.lower() or "distributed" in bullet.lower() or "ai" in bullet.lower()) and not (project.repo_url or project.demo_url)
           for project in tailored.projects for bullet in project.bullet_points):
        gaps.append("High-signal architecture or AI claims would be more credible with repo/demo links.")
    return gaps


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
                        "repo_url": project.repo_url,
                        "demo_url": project.demo_url,
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
    generic_summary = response.generic_summary or _has_generic_summary(tailored.professional_summary)
    shallow_ai_positioning = response.shallow_ai_positioning or _has_shallow_ai_positioning(job, tailored)
    weak_experience_framing = response.weak_experience_framing or _has_weak_experience_framing(job, tailored)
    credibility_gaps = list(dict.fromkeys(response.credibility_gaps + _credibility_gaps(tailored)))
    return ResumeReview(
        passed=response.passed and not generic_summary and not weak_experience_framing and not shallow_ai_positioning,
        underfilled=response.underfilled or heuristic_underfilled,
        generic_summary=generic_summary,
        shallow_ai_positioning=shallow_ai_positioning,
        weak_experience_framing=weak_experience_framing,
        missing_requirements=response.missing_requirements,
        duplicated_themes=response.duplicated_themes,
        unsupported_claims=response.unsupported_claims,
        trim_suggestions=response.trim_suggestions,
        page_fill_recommendations=page_fill_recommendations,
        credibility_gaps=credibility_gaps,
        issues=[ReviewIssue(severity=issue.severity, message=issue.message) for issue in response.issues],
    )
