"""Main tailor command — full resume tailoring pipeline."""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from ..utils.config_manager import load_config


def tailor(
    job_url: Optional[str] = typer.Option(None, "--job-url", "-j", help="URL of the job posting"),
    job_file: Optional[str] = typer.Option(None, "--job-file", help="Path to a text file with job posting content"),
    resume: Optional[str] = typer.Option(None, "--resume", "-r", help="Path to your LaTeX resume (.tex)"),
    projects: Optional[str] = typer.Option(None, "--projects", help="Path to projects registry file"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider (openai, anthropic, gemini)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model name"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", "-o", help="Output directory"),
    pdf: bool = typer.Option(True, "--pdf/--no-pdf", help="Compile PDF after editing LaTeX (default: on)"),
    linkedin: bool = typer.Option(False, "--linkedin", help="Generate a LinkedIn recruiter connect message"),
    recruiter: Optional[str] = typer.Option(None, "--recruiter", help="Recruiter's name for the LinkedIn message"),
    graduation: Optional[str] = typer.Option(None, "--graduation", help="Graduation timeline, e.g. 'May 2025'"),
    limit: int = typer.Option(300, "--limit", help="Max character limit for the LinkedIn message (default: 300)"),
    max_projects: int = typer.Option(4, "--max-projects", min=2, max=4, help="Maximum number of projects to include"),
    tailor_experience: bool = typer.Option(True, "--tailor-experience/--no-tailor-experience", help="Rewrite experience bullets for the role"),
    review: bool = typer.Option(True, "--review/--no-review", help="Run final quality review before writing output"),
    strict_truthfulness: bool = typer.Option(True, "--strict-truthfulness/--allow-approximations", help="Reject unsupported project metrics and claims"),
    fill_page: bool = typer.Option(True, "--fill-page/--no-fill-page", help="Use available page space for more high-signal content"),
    enrich_workers: int = typer.Option(4, "--enrich-workers", min=1, max=8, help="Number of parallel workers for project enrichment"),
):
    """Tailor your resume to a job posting using AI."""
    console = Console()
    config = load_config()

    if not job_url and not job_file:
        console.print("[red]Provide --job-url or --job-file[/red]")
        raise typer.Exit(1)

    # Resolve from flags → config → defaults
    resume = resume or config.get("resume")
    if not resume:
        console.print("[red]No resume path. Set it via --resume or: resume-tailor config set resume ~/path/to/resume.tex[/red]")
        raise typer.Exit(1)

    resume_path = Path(resume).expanduser()
    if not resume_path.exists():
        console.print(f"[red]Resume not found: {resume_path}[/red]")
        raise typer.Exit(1)

    projects = projects or config.get("projects", "./projects.md")
    projects_path = Path(projects).expanduser()
    if not projects_path.exists():
        console.print(f"[red]Projects registry not found: {projects_path}[/red]")
        console.print("[dim]Run 'resume-tailor scan' first to generate projects.md[/dim]")
        raise typer.Exit(1)

    provider = provider or config.get("provider", "gemini")
    output_dir = output_dir or config.get("output_dir", "./output")

    console.print(Panel.fit(
        f"[bold]Resume Tailor[/bold]\n"
        f"Provider: {provider}\n"
        f"Resume: {resume_path.name}\n"
        f"Projects: {projects_path}",
        border_style="blue",
    ))

    # Initialize LLM
    from ..ai.llm_client import get_llm_client
    try:
        llm = get_llm_client(provider=provider, model=model)
    except Exception as e:
        console.print(f"[red]Failed to initialize LLM: {e}[/red]")
        raise typer.Exit(1)

    # Wrap pipeline in try/except for clean error messages
    try:
        _run_pipeline(
            console,
            llm,
            job_url,
            job_file,
            resume_path,
            projects_path,
            output_dir,
            pdf,
            linkedin,
            recruiter,
            graduation,
            limit,
            max_projects,
            tailor_experience,
            review,
            strict_truthfulness,
            fill_page,
            enrich_workers,
        )
    except Exception as e:
        error_msg = str(e)
        if "RetryError" in type(e).__name__ and hasattr(e, "last_attempt"):
            error_msg = str(e.last_attempt.exception())
        console.print(f"\n[red]Error: {error_msg}[/red]")
        raise typer.Exit(1)


def _run_pipeline(
    console,
    llm,
    job_url,
    job_file,
    resume_path,
    projects_path,
    output_dir,
    pdf,
    linkedin=False,
    recruiter=None,
    graduation=None,
    limit=300,
    max_projects=4,
    tailor_experience=True,
    review=True,
    strict_truthfulness=True,
    fill_page=True,
    enrich_workers=4,
):
    """Run the 7-step tailoring pipeline."""
    # Step 1: Fetch job posting
    from ..core.job_fetcher import fetch_and_parse_job
    console.print("\n[bold]Step 1/7:[/bold] Fetching job posting...")
    job = fetch_and_parse_job(job_url, job_file, llm, console)
    console.print(f"  [green]Got: {job.title} at {job.company}[/green]")

    # Step 2: Parse resume
    from ..core.latex_parser import extract_existing_experience, extract_existing_skills, parse_resume
    console.print("\n[bold]Step 2/7:[/bold] Parsing resume...")
    parsed_resume = parse_resume(str(resume_path))
    existing_experience = extract_existing_experience(parsed_resume)
    existing_skills = extract_existing_skills(parsed_resume)
    console.print(f"  [green]Resume sections parsed ({len(existing_experience)} experience entries)[/green]")

    # Step 3: Load project registry (no LLM needed — instant)
    from ..core.project_registry import parse_projects_md
    console.print("\n[bold]Step 3/7:[/bold] Loading project registry...")
    registry = parse_projects_md(str(projects_path))
    console.print(f"  [green]Loaded {len(registry)} projects from registry[/green]")

    # Step 4: Enrich registry projects before matching
    from ..core.project_enricher import enrich_projects
    console.print("\n[bold]Step 4/7:[/bold] Enriching project evidence...")
    enriched_projects = enrich_projects(
        job=job,
        registry=registry,
        llm=llm,
        max_workers=enrich_workers,
        console=console,
    )
    console.print(f"  [green]Enriched {len(enriched_projects)} projects[/green]")

    # Step 5: Match and rank
    from ..core.project_matcher import match_projects
    console.print("\n[bold]Step 5/7:[/bold] Matching projects...")
    match_result = match_projects(job, enriched_projects, llm, max_projects=max_projects, console=console)

    # Step 6: Generate projects, experience, and skills
    from ..core.content_generator import generate_bullets
    from ..core.experience_generator import add_experience_bullet, tailor_experience as rewrite_experience
    from ..core.reviewer import review_resume, validate_project_bullets
    from ..core.skills_generator import tailor_skills
    from ..models.data_models import ResumeReview, TailoredResume
    from ..ai.schemas import SelectedProject
    console.print("\n[bold]Step 6/7:[/bold] Generating targeted content...")
    tailored_project_data = generate_bullets(match_result.selected_projects, job, enriched_projects, llm, console)

    tailored_projects = []
    unsupported_claims = []
    selected_source_names = set()
    enriched_lookup = {project.name.strip().lower(): project for project in enriched_projects}
    for selected_project, explicit_metrics, source_name in tailored_project_data:
        evidence = enriched_lookup.get(source_name.strip().lower())
        supported_terms = []
        if evidence:
            supported_terms = (
                evidence.tech
                + evidence.languages
                + evidence.key_features
                + evidence.architecture_signals
                + evidence.requirement_tags
            )
        issues = validate_project_bullets(
            selected_project.bullet_points,
            supported_terms=supported_terms,
            explicit_metrics=explicit_metrics,
            strict_truthfulness=strict_truthfulness,
        )
        if issues:
            unsupported_claims.extend([f"{selected_project.name}: {issue}" for issue in issues])
            if strict_truthfulness:
                console.print(f"[yellow]Warning: {selected_project.name} has unsupported claims; keeping review open[/yellow]")
        tailored_projects.append(selected_project)
        selected_source_names.add(source_name.strip().lower())

    tailored_experience = rewrite_experience(job, existing_experience, llm, console) if tailor_experience else []
    inventory = list(match_result.languages) + list(match_result.infrastructure_and_tools)
    for project in tailored_projects:
        inventory.extend([item.strip() for item in project.tech_stack_display.split(",") if item.strip()])
    tailored_skills = tailor_skills(job, existing_skills, inventory, llm, console)

    tailored = TailoredResume(
        professional_summary=match_result.professional_summary,
        projects=tailored_projects,
        experience=tailored_experience,
        skills=tailored_skills,
        review=ResumeReview(passed=not unsupported_claims, unsupported_claims=unsupported_claims),
    )

    if review:
        console.print("\n[bold]Step 7/7:[/bold] Reviewing tailored resume...")
        review_result = review_resume(job, tailored, llm, console)
        review_result.unsupported_claims = list(dict.fromkeys(review_result.unsupported_claims + unsupported_claims))
        review_result.passed = review_result.passed and not review_result.unsupported_claims
        tailored.review = review_result

        def _try_fill_page() -> bool:
            if not fill_page or not tailored.review.underfilled:
                return False

            experience_lookup = {
                (entry.company.strip().lower(), entry.role.strip().lower()): entry for entry in existing_experience
            }

            for idx, entry in enumerate(tailored.experience):
                key = (entry.company.strip().lower(), entry.role.strip().lower())
                source_entry = experience_lookup.get(key)
                if not source_entry or len(entry.bullet_points) >= min(3, max(3, len(source_entry.bullets))):
                    continue
                extra_bullet = add_experience_bullet(job, source_entry, entry, llm, console)
                if extra_bullet and extra_bullet not in entry.bullet_points:
                    tailored.experience[idx].bullet_points.append(extra_bullet)
                    return True

            if len(tailored.projects) < max_projects:
                remaining_projects = [
                    project for project in enriched_projects if project.name.strip().lower() not in selected_source_names
                ]
                if remaining_projects:
                    missing = {req.lower() for req in tailored.review.missing_requirements}

                    def _project_score(project):
                        req_overlap = sum(1 for tag in project.requirement_tags if tag.strip().lower() in missing)
                        tech_overlap = sum(1 for tech in project.tech if tech in job.tech_stack)
                        return (req_overlap, tech_overlap, len(project.explicit_metrics), len(project.architecture_signals))

                    next_project = sorted(remaining_projects, key=_project_score, reverse=True)[0]
                    extra_project_data = generate_bullets(
                        [
                            SelectedProject(
                                name=next_project.name,
                                relevance_score=0.75,
                                reasoning="Added to improve page fill and requirement coverage.",
                                suggested_angle=next_project.evidence_summary or "Highlight the most relevant technical depth.",
                            )
                        ],
                        job,
                        enriched_projects,
                        llm,
                        console,
                    )
                    if extra_project_data:
                        extra_project, explicit_metrics, source_name = extra_project_data[0]
                        issues = validate_project_bullets(
                            extra_project.bullet_points,
                            supported_terms=(
                                next_project.tech
                                + next_project.languages
                                + next_project.key_features
                                + next_project.architecture_signals
                                + next_project.requirement_tags
                            ),
                            explicit_metrics=explicit_metrics,
                            strict_truthfulness=strict_truthfulness,
                        )
                        if not issues:
                            tailored.projects.append(extra_project)
                            selected_source_names.add(source_name.strip().lower())
                            return True

            project_skill_tokens = {item.strip() for item in inventory if item.strip()}
            for skill in existing_skills.infrastructure_and_tools:
                if skill not in tailored.skills.infrastructure_and_tools and (
                    skill in job.tech_stack or skill in project_skill_tokens
                ):
                    tailored.skills.infrastructure_and_tools.append(skill)
                    return True

            for course in existing_skills.coursework:
                if course not in tailored.skills.coursework:
                    tailored.skills.coursework.append(course)
                    return True

            return False

        for _ in range(2):
            if not (fill_page and tailored.review.underfilled):
                break
            console.print("[dim]Resume is underfilled; adding more high-signal content...[/dim]")
            if not _try_fill_page():
                break
            review_result = review_resume(job, tailored, llm, console)
            review_result.unsupported_claims = list(dict.fromkeys(review_result.unsupported_claims + unsupported_claims))
            review_result.passed = review_result.passed and not review_result.unsupported_claims
            tailored.review = review_result

        if not tailored.review.passed or tailored.review.underfilled:
            console.print("[yellow]Review flagged issues in the tailored draft:[/yellow]")
            for issue in tailored.review.issues[:5]:
                console.print(f"  [yellow]- {issue.severity}: {issue.message}[/yellow]")
            for recommendation in tailored.review.page_fill_recommendations[:3]:
                console.print(f"  [yellow]- fill: {recommendation}[/yellow]")
    else:
        console.print("\n[bold]Step 7/7:[/bold] [dim]Review skipped (--no-review)[/dim]")

    # Edit LaTeX
    from ..core.latex_editor import edit_resume
    console.print("\n[bold]Editing:[/bold] Updating LaTeX...")
    new_tex = edit_resume(parsed_resume, tailored)

    # Save .tex — output/<date>/<company-position>.tex
    import re as _re
    from datetime import date
    from ..utils.file_utils import save_text

    def _slugify(text: str) -> str:
        text = text.lower().strip()
        text = _re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")

    today = date.today().strftime("%b-%d-%Y")
    company_slug = _slugify(job.company or "unknown")
    title_slug = _slugify(job.title or "unknown")
    filename = f"{company_slug}-{title_slug}"

    day_dir = Path(output_dir) / today
    tex_output = day_dir / f"{filename}.tex"
    save_text(new_tex, str(tex_output), console, f"Tailored .tex saved to {tex_output}")

    # Compile PDF
    if pdf:
        from ..core.pdf_compiler import compile_pdf
        console.print("\n[bold]Compile:[/bold] Compiling PDF...")
        pdf_path = compile_pdf(str(tex_output), str(day_dir), console)
        if pdf_path:
            console.print(f"[bold green]Done![/bold green] PDF → {pdf_path}")
    else:
        console.print("\n[bold]Step 7/7:[/bold] [dim]PDF compilation skipped (--no-pdf)[/dim]")
        console.print("\n[bold green]Done![/bold green]")

    if linkedin:
        from ..core.linkedin_generator import generate_linkedin_message
        console.print("\n[bold]LinkedIn:[/bold] Generating connect message...")
        msg = generate_linkedin_message(job, tailored, match_result, llm, recruiter, graduation, console, limit)
        if msg:
            char_count = len(msg)
            console.print(Rule(f"[green]LinkedIn Connect Message ({char_count}/{limit} chars)[/green]"))
            console.print(msg)
            console.print(Rule(style="green"))
