"""Main tailor command — full resume tailoring pipeline."""

import json
from pathlib import Path
from typing import List, Optional
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
        _run_pipeline(console, llm, job_url, job_file, resume_path, projects_path, output_dir, pdf, linkedin, recruiter, graduation, limit)
    except Exception as e:
        error_msg = str(e)
        if "RetryError" in type(e).__name__ and hasattr(e, "last_attempt"):
            error_msg = str(e.last_attempt.exception())
        console.print(f"\n[red]Error: {error_msg}[/red]")
        raise typer.Exit(1)


def _run_pipeline(console, llm, job_url, job_file, resume_path, projects_path, output_dir, pdf, linkedin=False, recruiter=None, graduation=None, limit=300):
    """Run the 7-step tailoring pipeline."""
    # Step 1: Fetch job posting
    from ..core.job_fetcher import fetch_and_parse_job
    console.print("\n[bold]Step 1/7:[/bold] Fetching job posting...")
    job = fetch_and_parse_job(job_url, job_file, llm, console)
    console.print(f"  [green]Got: {job.title} at {job.company}[/green]")

    # Step 2: Parse resume
    from ..core.latex_parser import parse_resume, extract_existing_projects
    console.print("\n[bold]Step 2/7:[/bold] Parsing resume...")
    parsed_resume = parse_resume(str(resume_path))
    existing_projects = extract_existing_projects(parsed_resume)
    console.print(f"  [green]Found {len(existing_projects)} existing projects[/green]")

    # Step 3: Load project registry (no LLM needed — instant)
    from ..core.project_registry import parse_projects_md
    console.print("\n[bold]Step 3/7:[/bold] Loading project registry...")
    registry = parse_projects_md(str(projects_path))
    console.print(f"  [green]Loaded {len(registry)} projects from registry[/green]")

    # Step 4: Match and rank (lightweight — just names/descriptions/tech)
    from ..core.project_matcher import match_projects
    console.print("\n[bold]Step 4/7:[/bold] Matching projects...")
    existing_text = json.dumps(existing_projects, indent=2)
    match_result = match_projects(job, registry, existing_text, llm, console)

    # Step 5: Deep-scan selected projects + generate bullets
    from ..core.content_generator import generate_bullets
    console.print("\n[bold]Step 5/7:[/bold] Deep-scanning selected projects & generating content...")
    tailored_projects = generate_bullets(match_result.selected_projects, job, registry, existing_projects, llm, console)

    # Build TailoredResume
    from ..models.data_models import TailoredResume
    tailored = TailoredResume(
        professional_summary=match_result.professional_summary,
        projects=tailored_projects,
        infrastructure_and_tools=match_result.infrastructure_and_tools,
    )

    # Step 6: Edit LaTeX
    from ..core.latex_editor import edit_resume
    console.print("\n[bold]Step 6/7:[/bold] Editing LaTeX...")
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

    # Step 7: Compile PDF
    if pdf:
        from ..core.pdf_compiler import compile_pdf
        console.print("\n[bold]Step 7/7:[/bold] Compiling PDF...")
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
