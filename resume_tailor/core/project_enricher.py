"""Build enriched project profiles before matching."""

import json
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from ..ai.llm_client import LLMClient
from ..ai.prompts import project_enrichment_prompt
from ..ai.schemas import EnrichedProjectResponse
from ..core.project_scanner import _build_dir_tree, _read_all_source_files, _read_dependency_files, _read_readme
from ..models.data_models import EnrichedProject, JobPosting, ProjectEntry


def _deep_scan_project(entry: ProjectEntry) -> str:
    """Read enough project context to ground enrichment."""
    project_root = Path(entry.path).expanduser().resolve()
    if not project_root.is_dir():
        parts = [
            f"Project: {entry.name}",
            f"Description: {entry.description}",
            f"Tech: {', '.join(entry.tech)}",
        ]
        if entry.key_features:
            parts.append(f"Key features: {' | '.join(entry.key_features)}")
        if entry.languages:
            parts.append(f"Languages: {', '.join(entry.languages)}")
        return "\n".join(parts)

    return (
        f"Project: {entry.name}\n"
        f"Description: {entry.description}\n"
        f"Tech: {', '.join(entry.tech)}\n"
        f"Key features: {' | '.join(entry.key_features)}\n"
        f"Languages: {', '.join(entry.languages)}\n\n"
        f"Directory structure:\n{_build_dir_tree(project_root)}\n\n"
        f"README:\n{_read_readme(project_root)}\n\n"
        f"Dependency / build files:\n{_read_dependency_files(project_root)}\n\n"
        f"Source code:\n{_read_all_source_files(project_root)}"
    )


def enrich_projects(
    registry: List[ProjectEntry],
    job: JobPosting,
    llm: LLMClient,
    console: Optional[Console] = None,
) -> List[EnrichedProject]:
    """Enrich registry projects with evidence-grounded summaries before selection."""
    job_json = json.dumps(
        {
            "title": job.title,
            "company": job.company,
            "responsibilities": job.responsibilities,
            "required_qualifications": job.required_qualifications,
            "preferred_qualifications": job.preferred_qualifications,
            "tech_stack": job.tech_stack,
        },
        indent=2,
    )

    deduped: dict[str, ProjectEntry] = {}
    duplicate_count = 0
    for entry in registry:
        key = entry.name.strip().lower()
        if key in deduped:
            duplicate_count += 1
            continue
        deduped[key] = entry

    if duplicate_count and console:
        console.print(f"[yellow]Warning: removed {duplicate_count} duplicate project registry entr(y/ies) before enrichment[/yellow]")

    enriched: List[EnrichedProject] = []
    for entry in deduped.values():
        if console:
            console.print(f"  [dim]Enriching {entry.name}...[/dim]")

        deep_context = _deep_scan_project(entry)
        prompt = project_enrichment_prompt(
            project_json=json.dumps(
                {
                    "name": entry.name,
                    "path": entry.path,
                    "description": entry.description,
                    "tech": entry.tech,
                    "key_features": entry.key_features,
                    "languages": entry.languages,
                },
                indent=2,
            ),
            deep_context=deep_context,
            job_posting_json=job_json,
        )

        data = llm.generate_structured(prompt, EnrichedProjectResponse, temperature=0.2)
        enriched.append(
            EnrichedProject(
                name=data.name or entry.name,
                path=entry.path,
                description=data.description or entry.description,
                tech=data.tech or entry.tech,
                key_features=data.key_features or entry.key_features,
                languages=data.languages or entry.languages,
                architecture_signals=data.architecture_signals,
                outcomes=data.outcomes,
                explicit_metrics=data.explicit_metrics,
                evidence_summary=data.evidence_summary,
                requirement_tags=data.requirement_tags,
            )
        )

    return enriched
