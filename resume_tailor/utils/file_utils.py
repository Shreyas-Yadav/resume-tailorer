"""File I/O utility functions."""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from rich.console import Console


def save_json(
    data: Dict[str, Any],
    filepath: str,
    console: Optional[Console] = None,
    success_message: Optional[str] = None,
) -> None:
    """Save data as JSON file with error handling."""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        if console:
            msg = success_message or f"Results saved to {filepath}"
            console.print(f"\n[green]{msg}[/green]")
    except (IOError, OSError) as e:
        if console:
            console.print(f"[red]Failed to save file: {e}[/red]")
        raise
    except TypeError as e:
        if console:
            console.print(f"[red]Data is not JSON serializable: {e}[/red]")
        raise


def save_text(
    content: str,
    filepath: str,
    console: Optional[Console] = None,
    success_message: Optional[str] = None,
) -> None:
    """Save text content to file with error handling."""
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        if console:
            msg = success_message or f"Results saved to {filepath}"
            console.print(f"\n[green]{msg}[/green]")
    except (IOError, OSError) as e:
        if console:
            console.print(f"[red]Failed to save file: {e}[/red]")
        raise
