"""Parse a LaTeX resume into structured sections."""

import re
from typing import List, Tuple
from ..models.data_models import ExistingResume, ResumeSection


# Sections we expect to find (in order)
EXPECTED_SECTIONS = [
    "Professional Summary",
    "Experience",
    "Projects",
    "Education",
    "Technical Skills",
]


def _find_section_boundaries(lines: List[str]) -> List[Tuple[str, int, int]]:
    """Find start/end line indices for each \\section{...} block."""
    sections = []
    section_pattern = re.compile(r"\\section\{(.+?)\}")

    for i, line in enumerate(lines):
        match = section_pattern.search(line)
        if match:
            sections.append((match.group(1), i, -1))  # end TBD

    # Set end of each section to start of next (or end of doc)
    for idx in range(len(sections)):
        if idx + 1 < len(sections):
            raw_end = sections[idx + 1][1]
        else:
            # Last section ends at \end{document} or EOF
            raw_end = len(lines)
            for j in range(sections[idx][1], len(lines)):
                if r"\end{document}" in lines[j]:
                    raw_end = j
                    break

        # Trim trailing blank lines and comment-only lines so that
        # inter-section separators (e.g. %-----------EXPERIENCE-----------)
        # are preserved when sections get replaced.
        end = raw_end
        while end > sections[idx][1]:
            stripped = lines[end - 1].strip()
            if stripped == "" or stripped.startswith("%"):
                end -= 1
            else:
                break

        sections[idx] = (sections[idx][0], sections[idx][1], end)

    return sections


def _make_section(name: str, start: int, end: int, lines: List[str]) -> ResumeSection:
    """Create a ResumeSection from line range."""
    raw = "\n".join(lines[start:end])
    return ResumeSection(name=name, start_line=start, end_line=end, raw_content=raw)


def parse_resume(filepath: str) -> ExistingResume:
    """Parse a LaTeX resume file into structured ExistingResume."""
    with open(filepath, "r") as f:
        content = f.read()

    lines = content.split("\n")

    # Find \begin{document}
    doc_start = 0
    for i, line in enumerate(lines):
        if r"\begin{document}" in line:
            doc_start = i
            break

    # Find \end{document}
    doc_end = len(lines)
    for i, line in enumerate(lines):
        if r"\end{document}" in line:
            doc_end = i
            break

    preamble = "\n".join(lines[: doc_start + 1])
    postamble = "\n".join(lines[doc_end:])

    # Find sections
    boundaries = _find_section_boundaries(lines)
    section_map = {}
    for name, start, end in boundaries:
        section_map[name] = _make_section(name, start, end, lines)

    # Heading is between \begin{document} and first section
    first_section_start = boundaries[0][1] if boundaries else doc_end
    heading = "\n".join(lines[doc_start + 1 : first_section_start])

    # Map to expected sections (use empty sections if missing)
    def get_section(name: str) -> ResumeSection:
        if name in section_map:
            return section_map[name]
        return ResumeSection(name=name, start_line=0, end_line=0, raw_content="")

    return ExistingResume(
        preamble=preamble,
        heading=heading,
        summary=get_section("Professional Summary"),
        experience=get_section("Experience"),
        projects=get_section("Projects"),
        education=get_section("Education"),
        skills=get_section("Technical Skills"),
        postamble=postamble,
        raw_lines=lines,
    )


def extract_existing_projects(resume: ExistingResume) -> List[dict]:
    """Extract project names and details from the existing resume's Projects section."""
    projects = []
    content = resume.projects.raw_content
    # Find \resumeProjectHeading lines
    heading_pattern = re.compile(
        r"\\resumeProjectHeading\s*\n?\s*\{\\textbf\{(.+?)\}\s*\$\|\$\s*\\emph\{(.+?)\}\}"
    )
    # Split by project headings
    headings = list(heading_pattern.finditer(content))

    for i, match in enumerate(headings):
        name = match.group(1)
        tech = match.group(2)
        # Get content until next heading or end
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        block = content[start:end]

        # Extract bullet points
        bullets = re.findall(r"\\resumeItem\{(.+?)\}", block, re.DOTALL)
        bullets = [b.strip() for b in bullets]

        projects.append({
            "name": name,
            "tech_stack": tech,
            "bullets": bullets,
        })

    return projects
