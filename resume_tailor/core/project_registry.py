"""Parse and write the projects.md registry file."""

import re
from pathlib import Path
from typing import List

from ..models.data_models import ProjectEntry


def parse_projects_md(filepath: str) -> List[ProjectEntry]:
    """Parse a projects.md file into a list of ProjectEntry objects.

    Expected format:
        ## Project Name
        - **Path:** ~/path/to/project
        - **Description:** Brief description of the project
        - **Tech:** Python, AWS, Docker
    """
    path = Path(filepath).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Projects file not found: {filepath}")

    content = path.read_text()
    entries = []

    # Split by ## headings
    sections = re.split(r"^## ", content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n")
        name = lines[0].strip()
        if not name:
            continue

        body = "\n".join(lines[1:])

        proj_path = _extract_field(body, "Path") or ""
        description = _extract_field(body, "Description") or ""
        tech_str = _extract_field(body, "Tech") or ""
        tech = [t.strip() for t in tech_str.split(",") if t.strip()]

        entries.append(ProjectEntry(
            name=name,
            path=proj_path,
            description=description,
            tech=tech,
        ))

    return entries


def _extract_field(text: str, field_name: str) -> str:
    """Extract a field value from markdown list item: - **Field:** value"""
    pattern = rf"\*\*{field_name}:\*\*\s*(.+)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def write_projects_md(filepath: str, entries: List[ProjectEntry]) -> None:
    """Write a list of ProjectEntry objects to a projects.md file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Projects Registry", ""]

    for entry in entries:
        lines.append(f"## {entry.name}")
        lines.append(f"- **Path:** {entry.path}")
        lines.append(f"- **Description:** {entry.description}")
        lines.append(f"- **Tech:** {', '.join(entry.tech)}")
        lines.append("")

    path.write_text("\n".join(lines))
