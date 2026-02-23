"""Compile LaTeX to PDF using pdflatex."""

import shutil
import subprocess
from pathlib import Path
from typing import Optional
from rich.console import Console

PDFLATEX_TIMEOUT = 120  # seconds — allow extra time for large/complex documents


def compile_pdf(
    tex_path: str,
    output_dir: str,
    console: Optional[Console] = None,
) -> Optional[str]:
    """Compile a .tex file to PDF using pdflatex.

    Returns the path to the generated PDF, or None if pdflatex is not available.
    """
    if not shutil.which("pdflatex"):
        if console:
            console.print(
                "[yellow]pdflatex not found. Install TeX Live or MacTeX to compile PDFs.[/yellow]\n"
                "  macOS: brew install --cask mactex\n"
                "  Ubuntu: sudo apt install texlive-full"
            )
        return None

    tex_file = Path(tex_path)
    pdf_dir = Path(output_dir)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    if console:
        console.print("[dim]Compiling LaTeX to PDF...[/dim]")

    # Run pdflatex twice (for references)
    for run in range(2):
        result = subprocess.run(
            [
                "pdflatex",
                "-interaction=nonstopmode",
                f"-output-directory={pdf_dir}",
                str(tex_file),
            ],
            capture_output=True,
            text=True,
            timeout=PDFLATEX_TIMEOUT,
        )
        if result.returncode != 0 and run == 1:
            if console:
                # Show last 20 lines of log for debugging
                log_lines = result.stdout.split("\n")[-20:]
                console.print("[red]pdflatex compilation failed:[/red]")
                for line in log_lines:
                    if line.strip():
                        console.print(f"  [dim]{line}[/dim]")
                log_file = pdf_dir / (tex_file.stem + ".log")
                console.print(f"[yellow]Full log: {log_file}[/yellow]")
            return None

    # Always clean non-log auxiliary files
    pdf_name = tex_file.stem + ".pdf"
    for ext in [".aux", ".out", ".fls", ".fdb_latexmk", ".synctex.gz"]:
        aux_file = pdf_dir / (tex_file.stem + ext)
        if aux_file.exists():
            aux_file.unlink()

    # Only delete log on success (preserve it for debugging on failure)
    log_file = pdf_dir / (tex_file.stem + ".log")
    pdf_path = pdf_dir / pdf_name
    if pdf_path.exists() and log_file.exists():
        log_file.unlink()

    if pdf_path.exists():
        if console:
            console.print(f"[green]PDF compiled: {pdf_path}[/green]")
        return str(pdf_path)

    return None
