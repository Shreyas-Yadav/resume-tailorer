"""Standalone scan command to discover projects and write their paths to a file."""

from typing import List
import typer
from rich.console import Console


def scan(
    dir: List[str] = typer.Option(..., "--dir", "-d", help="Directories to scan for projects"),
    output: str = typer.Option("./projects.txt", "--output", "-o", help="Output path for discovered project paths"),
):
    """Recursively scan directories and write all discovered project paths to a file."""
    console = Console()

    from ..core.project_scanner import find_project_roots

    console.print(f"[dim]Scanning {len(dir)} director{'y' if len(dir) == 1 else 'ies'}...[/dim]")
    roots = find_project_roots(dir)

    if not roots:
        console.print("[yellow]No projects found.[/yellow]")
        raise typer.Exit()

    with open(output, "w") as f:
        for root in roots:
            f.write(str(root) + "\n")

    console.print(f"[green]Found {len(roots)} project(s). Paths written to {output}[/green]")
