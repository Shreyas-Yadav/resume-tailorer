"""Generate tailored bullet points for selected projects."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import (
    bullet_planning_prompt,
    bullet_repair_prompt,
    bullet_scoring_prompt,
    planned_bullet_generation_prompt,
)
from ..ai.schemas import (
    BulletPlanResponse,
    BulletPointsResponse,
    BulletRepairResponse,
    BulletScoreResponse,
    SelectedProject,
)
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
    """Get rich project context, display tech, key features, explicit metrics, and project links."""
    entry = _find_registry_entry(name, registry)
    if entry:
        if console:
            console.print(f"    [dim]Using enriched evidence for {entry.name}...[/dim]")
        description = "\n".join(
            [
                f"Description: {entry.description}",
                f"Evidence summary: {entry.evidence_summary}",
                f"Architecture: {' | '.join(entry.architecture_signals)}",
                f"Workflow: {' | '.join(entry.workflow_signals)}",
                f"Automation: {' | '.join(entry.automation_signals)}",
                f"Outcomes: {' | '.join(entry.outcomes)}",
                f"Explicit metrics: {' | '.join(entry.explicit_metrics)}",
                f"Result signals: {' | '.join(entry.result_signals)}",
                f"Repo: {entry.repo_url or '(none)'}",
                f"Demo: {entry.demo_url or '(none)'}",
            ]
        )
        return description, ", ".join(entry.tech), entry.key_features, entry.explicit_metrics, entry.repo_url, entry.demo_url

    if console:
        console.print(f"    [yellow]Warning: no context found for project '{name}' — bullets may be generic[/yellow]")
    return "", "", [], [], "", ""


def _collect_global_themes(existing_resume_themes: Optional[List[str]], used_competencies: List[str]) -> List[str]:
    themes = []
    if existing_resume_themes:
        themes.extend(existing_resume_themes)
    themes.extend(used_competencies)
    deduped = []
    seen = set()
    for theme in themes:
        normalized = theme.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(theme)
    return deduped


def _score_total(scores: List[int]) -> int:
    return sum(scores)


def generate_bullets(
    selected_projects: List[SelectedProject],
    job: JobPosting,
    registry: List[EnrichedProject],
    requirement_themes: Optional[List[str]],
    llm: LLMClient,
    existing_resume_themes: Optional[List[str]] = None,
    max_workers: int = 2,
    console: Optional[Console] = None,
) -> List[tuple[TailoredProject, List[str], str]]:
    """Generate tailored bullet points using plan, score, and selective repair stages."""
    if console:
        console.print("[dim]Generating tailored bullet points...[/dim]")

    job_tech = ", ".join(job.tech_stack)
    used_competencies: List[str] = []
    requirement_themes = requirement_themes or []

    def _generate_for_project(
        proj_info: SelectedProject,
        global_themes: List[str],
    ) -> tuple[TailoredProject, List[str], str, List[str]]:
        name = proj_info.name
        angle = proj_info.suggested_angle

        if console:
            console.print(f"  [dim]Writing bullets for {short_project_display(name)}...[/dim]")

        desc, tech, key_features, explicit_metrics, repo_url, demo_url = _get_project_context(name, registry, console)

        if console:
            console.print(f"    [dim]Planning bullets for {short_project_display(name)}...[/dim]")
        plan_prompt = bullet_planning_prompt(
            project_name=name,
            project_context=desc,
            project_tech=tech,
            job_title=job.title,
            job_tech=job_tech,
            suggested_angle=angle,
            requirement_themes=requirement_themes,
            existing_resume_themes=global_themes,
        )
        plan = llm.generate_structured(plan_prompt, BulletPlanResponse, temperature=0.3)
        plan_json = json.dumps(
            {
                "display_name": plan.display_name,
                "tech_stack_display": plan.tech_stack_display,
                "bullet_plan": [
                    {
                        "competency": item.competency,
                        "requirement_theme": item.requirement_theme,
                        "evidence": item.evidence,
                        "target_outcome": item.target_outcome,
                    }
                    for item in plan.bullet_plan
                ],
            },
            indent=2,
        )

        if console:
            console.print(f"    [dim]Drafting bullets for {short_project_display(name)}...[/dim]")
        draft_prompt = planned_bullet_generation_prompt(
            project_name=name,
            project_context=desc,
            project_tech=tech,
            job_title=job.title,
            job_tech=job_tech,
            bullet_plan_json=plan_json,
        )
        data = llm.generate_structured(draft_prompt, BulletPointsResponse, temperature=0.45)

        if console:
            console.print(f"    [dim]Scoring bullets for {short_project_display(name)}...[/dim]")
        scoring_prompt = bullet_scoring_prompt(
            project_name=name,
            job_title=job.title,
            requirement_themes=requirement_themes,
            bullet_plan_json=plan_json,
            bullet_points=data.bullet_points,
        )
        score = llm.generate_structured(scoring_prompt, BulletScoreResponse, temperature=0.2)

        final_bullets = list(data.bullet_points)
        score_map = {item.bullet_index: item for item in score.scored_bullets}
        for repair_round in range(2):
            failing_indexes = [
                idx for idx, item in score_map.items()
                if not item.passes or _score_total(item.scores) < 22 or item.scores[4] < 3 or item.scores[1] < 3
            ]
            if not failing_indexes:
                break

            if console:
                console.print(f"    [dim]Repairing {len(failing_indexes)} weak bullet(s) for {short_project_display(name)} (round {repair_round + 1})...[/dim]")

            for bullet_index in failing_indexes:
                plan_item = plan.bullet_plan[min(bullet_index, len(plan.bullet_plan) - 1)]
                repair_prompt = bullet_repair_prompt(
                    project_name=name,
                    project_context=desc,
                    project_tech=tech,
                    job_title=job.title,
                    plan_item_json=json.dumps(
                        {
                            "competency": plan_item.competency,
                            "requirement_theme": plan_item.requirement_theme,
                            "evidence": plan_item.evidence,
                            "target_outcome": plan_item.target_outcome,
                        },
                        indent=2,
                    ),
                    current_bullet=final_bullets[bullet_index],
                    repair_instruction=score_map[bullet_index].repair_instruction or "Make the bullet more specific, distinct, and concrete.",
                )
                repaired = llm.generate_structured(repair_prompt, BulletRepairResponse, temperature=0.35)
                if repaired.bullet_point:
                    final_bullets[bullet_index] = repaired.bullet_point

            if console:
                console.print(f"    [dim]Re-scoring bullets for {short_project_display(name)}...[/dim]")
            rescoring_prompt = bullet_scoring_prompt(
                project_name=name,
                job_title=job.title,
                requirement_themes=requirement_themes,
                bullet_plan_json=plan_json,
                bullet_points=final_bullets,
            )
            score = llm.generate_structured(rescoring_prompt, BulletScoreResponse, temperature=0.2)
            score_map = {item.bullet_index: item for item in score.scored_bullets}

        accepted_display_name = data.display_name or plan.display_name or name
        accepted_tech_stack = data.tech_stack_display or plan.tech_stack_display or tech

        return (
            TailoredProject(
                name=accepted_display_name,
                tech_stack_display=accepted_tech_stack,
                bullet_points=final_bullets,
                repo_url=repo_url,
                demo_url=demo_url,
            ),
            explicit_metrics,
            name,
            [item.competency for item in plan.bullet_plan],
        )

    if len(selected_projects) <= 1:
        result = _generate_for_project(
            selected_projects[0],
            _collect_global_themes(existing_resume_themes, used_competencies),
        ) if selected_projects else None
        if not result:
            return []
        project, explicit_metrics, source_name, competencies = result
        used_competencies.extend(competencies)
        return [(project, explicit_metrics, source_name)]

    max_workers = max(1, min(max_workers, len(selected_projects)))
    prepared = [
        (
            index,
            proj_info,
            _collect_global_themes(existing_resume_themes, used_competencies),
        )
        for index, proj_info in enumerate(selected_projects)
    ]

    completed: dict[int, tuple[TailoredProject, List[str], str, List[str]]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_generate_for_project, proj_info, global_themes): index
            for index, proj_info, global_themes in prepared
        }
        for future in as_completed(futures):
            index = futures[future]
            completed[index] = future.result()

    tailored: List[tuple[TailoredProject, List[str], str]] = []
    for index in range(len(prepared)):
        project, explicit_metrics, source_name, competencies = completed[index]
        used_competencies.extend(competencies)
        tailored.append((project, explicit_metrics, source_name))

    return tailored
