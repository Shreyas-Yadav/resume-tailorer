"""Typer app setup and global options."""

import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    name="resume-tailor",
    help="Tailor your LaTeX resume to any job description using LLMs.",
    no_args_is_help=True,
)

# Import and register subcommands
from .tailor import tailor  # noqa: E402
from .scan import scan  # noqa: E402
from .config import config_app  # noqa: E402

app.command()(tailor)
app.command()(scan)
app.add_typer(config_app, name="config", help="Manage configuration.")
