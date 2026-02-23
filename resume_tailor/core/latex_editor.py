"""Splice tailored content into a LaTeX resume."""

import re
from typing import List
from ..models.data_models import ExistingResume, TailoredProject, TailoredResume


def _markdown_bold_to_latex(text: str) -> str:
    """Convert **bold** to \\textbf{bold} and escape special chars."""
    # Escape & and % (but not backslashes we'll add)
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    # Convert **bold** to \textbf{bold}
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    return text


def _build_summary_section(summary_text: str) -> str:
    """Build the Professional Summary LaTeX section."""
    converted = _markdown_bold_to_latex(summary_text)
    return (
        f"\\section{{Professional Summary}}\n"
        f" \\begin{{itemize}}[leftmargin=0.15in, label={{}}]\n"
        f"    \\small{{\\item{{\n"
        f"     {converted}\n"
        f"    }}}}\n"
        f" \\end{{itemize}}"
    )


def _build_projects_section(projects: List[TailoredProject]) -> str:
    """Build the Projects LaTeX section."""
    lines = [
        "\\section{Projects}",
        "    \\resumeSubHeadingListStart",
    ]

    for proj in projects:
        name = _markdown_bold_to_latex(proj.name)
        tech = proj.tech_stack_display
        lines.append("")
        lines.append(f"    \\resumeProjectHeading")
        lines.append(f"        {{\\textbf{{{name}}} $|$ \\emph{{{tech}}}}}{{}}")
        lines.append(f"        \\resumeItemListStart")

        for bullet in proj.bullet_points:
            converted = _markdown_bold_to_latex(bullet)
            lines.append(f"        \\resumeItem{{{converted}}}")

        lines.append(f"        \\resumeItemListEnd")

    lines.append("    \\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _build_skills_section(skills: dict) -> str:
    """Build the Technical Skills LaTeX section."""
    languages = skills.get("languages", "")
    infra = skills.get("infrastructure_and_tools", "")
    coursework = skills.get("coursework", "")

    return (
        f"\\section{{Technical Skills}}\n"
        f" \\begin{{itemize}}[leftmargin=0.15in, label={{}}]\n"
        f"    \\small{{\\item{{\n"
        f"     \\textbf{{Languages}}{{: {languages}}} \\\\\n"
        f"     \\textbf{{Infrastructure \\& Tools}}{{: {infra}}} \\\\\n"
        f"     \\textbf{{Coursework}}{{: {coursework}}}\n"
        f"    }}}}\n"
        f" \\end{{itemize}}"
    )


def edit_resume(
    resume: ExistingResume,
    tailored: TailoredResume,
) -> str:
    """Splice tailored content into the resume, replacing only summary and projects.

    Skills, experience, and education are left untouched.
    Replaces in reverse document order (projects → summary) to avoid line-number shifts.
    """
    lines = list(resume.raw_lines)

    # Replace Infrastructure & Tools line in skills section (in-place, no line count change)
    if tailored.infrastructure_and_tools:
        infra_pattern = re.compile(r"(\\textbf\{Infrastructure \\& Tools\}\{: ).+(\})")
        for i in range(resume.skills.start_line, resume.skills.end_line):
            if infra_pattern.search(lines[i]):
                lines[i] = infra_pattern.sub(
                    rf"\g<1>{tailored.infrastructure_and_tools}\2", lines[i]
                )
                break

    new_projects = _build_projects_section(tailored.projects)
    new_summary = _build_summary_section(tailored.professional_summary)

    # Replace projects first (comes later in the document)
    projects_lines = new_projects.split("\n")
    lines[resume.projects.start_line : resume.projects.end_line] = projects_lines

    proj_delta = len(projects_lines) - (resume.projects.end_line - resume.projects.start_line)

    # Replace summary. If summary comes after the projects block (unusual layout),
    # adjust its line numbers by the delta introduced by the projects replacement.
    # The shift boundary is projects.end_line — everything at or after that point moved.
    sum_start = resume.summary.start_line
    sum_end = resume.summary.end_line
    if sum_start >= resume.projects.end_line:
        sum_start += proj_delta
        sum_end += proj_delta

    summary_lines = new_summary.split("\n")
    lines[sum_start:sum_end] = summary_lines

    return "\n".join(lines)
