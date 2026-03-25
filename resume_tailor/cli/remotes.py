"""Populate repo URLs in projects.md from local git remotes."""

from pathlib import Path

import typer
from rich.console import Console


def remotes(
    projects: str = typer.Option("./projects.md", "--projects", "-p", help="Path to projects.md registry"),
):
    """Read each project path and write detected git remote URLs back to the registry."""
    console = Console()

    from ..core.git_remote import get_git_remote_url
    from ..core.project_registry import parse_projects_md, write_projects_md

    projects_path = Path(projects).expanduser()
    if not projects_path.exists():
        console.print(f"[red]Projects registry not found: {projects_path}[/red]")
        raise typer.Exit(code=1)

    entries = parse_projects_md(str(projects_path))
    if not entries:
        console.print("[yellow]No project entries found in the registry.[/yellow]")
        raise typer.Exit()

    updated = 0
    missing = 0

    for entry in entries:
        console.print(f"[dim]Inspecting {entry.name}...[/dim]")
        repo_url = get_git_remote_url(entry.path)
        if repo_url:
            if entry.repo_url != repo_url:
                entry.repo_url = repo_url
                updated += 1
            console.print(f"  [green]{repo_url}[/green]")
        else:
            missing += 1
            console.print("  [yellow]No git remote found[/yellow]")

    write_projects_md(str(projects_path), entries)
    console.print(
        f"[green]Updated {updated} project(s)[/green]"
        f"{'' if not missing else f' [yellow]({missing} without remotes)[/yellow]'}"
    )
