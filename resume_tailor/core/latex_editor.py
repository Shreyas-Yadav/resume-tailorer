"""Splice tailored content into a LaTeX resume."""

import re
from typing import List
from ..models.data_models import ExistingResume, TailoredExperienceEntry, TailoredProject, TailoredResume, TailoredSkills


def _markdown_bold_to_latex(text: str) -> str:
    """Convert **bold** to \\textbf{bold} and escape special chars."""
    # Escape common LaTeX special chars while preserving inserted commands.
    text = text.replace("\\", r"\textbackslash ")
    text = text.replace("&", r"\&")
    text = text.replace("%", r"\%")
    text = text.replace("_", r"\_")
    text = text.replace("#", r"\#")
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
        links = []
        if proj.repo_url:
            links.append(rf"\href{{{proj.repo_url}}}{{\underline{{GitHub}}}}")
        if proj.demo_url:
            links.append(rf"\href{{{proj.demo_url}}}{{\underline{{Demo}}}}")
        right_col = " $|$ ".join(links)
        lines.append("")
        lines.append(f"    \\resumeProjectHeading")
        lines.append(f"        {{\\textbf{{{name}}} $|$ \\emph{{{tech}}}}}{{{right_col}}}")
        lines.append(f"        \\resumeItemListStart")

        for bullet in proj.bullet_points:
            converted = _markdown_bold_to_latex(bullet)
            lines.append(f"        \\resumeItem{{{converted}}}")

        lines.append(f"        \\resumeItemListEnd")

    lines.append("    \\resumeSubHeadingListEnd")
    return "\n".join(lines)


def _build_experience_section(entries: List[TailoredExperienceEntry], fallback_raw: str) -> str:
    """Build an updated Experience section while preserving subheading structure."""
    if not entries:
        return fallback_raw

    pattern = re.compile(
        r"(\\section\{Experience\}\s*\\resumeSubHeadingListStart)?(?P<body>.*?)(\\resumeSubHeadingListEnd)",
        re.DOTALL,
    )
    body_match = pattern.search(fallback_raw)
    if not body_match:
        return fallback_raw

    entry_pattern = re.compile(
        r"(\\resumeSubheading\s*\n\s*\{(?P<role>.+?)\}\{.+?\}\s*\n\s*\{(?P<company>.+?)\}\{.+?\}\s*\n\s*\\resumeItemListStart)(?P<bullets>.*?)(\\resumeItemListEnd)",
        re.DOTALL,
    )
    replacements = {(e.company.strip().lower(), e.role.strip().lower()): e for e in entries}

    def _replace(match: re.Match) -> str:
        key = (match.group("company").strip().lower(), match.group("role").strip().lower())
        tailored = replacements.get(key)
        if not tailored:
            return match.group(0)

        bullet_lines = []
        for bullet in tailored.bullet_points:
            bullet_lines.append(f"        \\resumeItem{{{_markdown_bold_to_latex(bullet)}}}")
        bullets = "\n".join(bullet_lines)
        return f"{match.group(1)}\n{bullets}\n        \\resumeItemListEnd"

    new_body = entry_pattern.sub(_replace, body_match.group("body"))
    return "\\section{Experience}\n  \\resumeSubHeadingListStart" + new_body + "\\resumeSubHeadingListEnd"


def _build_skills_section(skills: TailoredSkills) -> str:
    """Build the Technical Skills LaTeX section."""
    languages = ", ".join(skills.languages)
    infra = ", ".join(skills.infrastructure_and_tools)
    coursework = ", ".join(skills.coursework)

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
    """Splice tailored content into the resume, replacing summary, experience, projects, and skills."""
    lines = list(resume.raw_lines)

    replacements = [
        (resume.skills, _build_skills_section(tailored.skills)),
        (resume.projects, _build_projects_section(tailored.projects)),
        (resume.experience, _build_experience_section(tailored.experience, resume.experience.raw_content)),
        (resume.summary, _build_summary_section(tailored.professional_summary)),
    ]

    for section, replacement in sorted(replacements, key=lambda item: item[0].start_line, reverse=True):
        if not section.raw_content:
            continue
        lines[section.start_line:section.end_line] = replacement.split("\n")

    return "\n".join(lines)
