"""Profile command: read project paths from projects.txt, LLM-profile each, write projects.md."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console


def profile(
    input: str = typer.Option("./projects.txt", "--input", "-i", help="Path to projects.txt from scan"),
    output: str = typer.Option("./projects.md", "--output", "-o", help="Output path for projects.md registry"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="LLM provider (openai, anthropic, gemini)"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model name"),
):
    """Read project paths from projects.txt, LLM-profile each one, and write projects.md."""
    console = Console()

    from ..ai.llm_client import get_llm_client
    from ..core.project_scanner import profile_projects
    from ..core.project_registry import write_projects_md
    from ..models.data_models import ProjectEntry

    # Read and validate paths from input file
    input_path = Path(input).expanduser()
    if not input_path.exists():
        console.print(f"[red]Input file not found: {input}[/red]")
        raise typer.Exit(code=1)

    raw_lines = input_path.read_text(encoding="utf-8").splitlines()
    path_strings = [line.strip() for line in raw_lines if line.strip()]

    if not path_strings:
        console.print(f"[yellow]No paths found in {input}.[/yellow]")
        raise typer.Exit()

    # Validate each path
    roots = []
    for p in path_strings:
        resolved = Path(p).expanduser()
        if resolved.is_dir():
            roots.append(resolved)
        else:
            console.print(f"[yellow]Skipping (not a directory): {p}[/yellow]")

    if not roots:
        console.print("[red]No valid project directories found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[dim]Profiling {len(roots)} project(s) with LLM...[/dim]")

    llm = get_llm_client(provider, model)
    profiles = profile_projects(roots, llm, console)

    if not profiles:
        console.print("[yellow]No projects were successfully profiled.[/yellow]")
        raise typer.Exit()

    entries = [
        ProjectEntry(
            name=p.name,
            path=p.path,
            description=p.description,
            tech=p.tech_stack,
            key_features=p.key_features,
            languages=p.languages,
        )
        for p in profiles
    ]

    write_projects_md(output, entries)
    console.print(f"[green]Profiled {len(entries)} project(s). Registry written to {output}[/green]")
