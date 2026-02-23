"""Config management commands."""

import typer
from rich.console import Console
from rich.table import Table

from ..utils.config_manager import load_config, save_config, set_config_value, CONFIG_FILE

config_app = typer.Typer(no_args_is_help=True)
console = Console()


@config_app.command("show")
def config_show():
    """Show current configuration."""
    config = load_config()

    table = Table(title="Resume Tailor Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    import os
    for key, value in config.items():
        source = "env" if key == "provider" and os.getenv("AI_PROVIDER") else "file" if CONFIG_FILE.exists() else "default"
        table.add_row(key, str(value) if value else "(not set)", source)

    console.print(table)
    console.print(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Config key (e.g., provider, model, output_dir)"),
    value: str = typer.Argument(help="Config value"),
):
    """Set a configuration value."""
    valid_keys = {"provider", "model", "resume", "projects", "output_dir"}
    if key not in valid_keys:
        console.print(f"[red]Invalid key: {key}. Valid keys: {', '.join(sorted(valid_keys))}[/red]")
        raise typer.Exit(1)

    if key == "provider" and value not in {"openai", "anthropic", "gemini"}:
        console.print(f"[red]Invalid provider: {value}. Choose: openai, anthropic, gemini[/red]")
        raise typer.Exit(1)

    set_config_value(key, value)
    console.print(f"[green]Set {key} = {value}[/green]")


@config_app.command("init")
def config_init():
    """Initialize default configuration file."""
    if CONFIG_FILE.exists():
        console.print(f"[yellow]Config file already exists: {CONFIG_FILE}[/yellow]")
        overwrite = typer.confirm("Overwrite?")
        if not overwrite:
            raise typer.Exit()

    from ..utils.config_manager import DEFAULT_CONFIG
    save_config(DEFAULT_CONFIG)
    console.print(f"[green]Config initialized at {CONFIG_FILE}[/green]")
