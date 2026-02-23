"""Data models for the resume tailor pipeline."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class JobPosting:
    url: str
    title: str
    company: str
    responsibilities: List[str]
    required_qualifications: List[str]
    preferred_qualifications: List[str]
    tech_stack: List[str]


@dataclass
class ProjectEntry:
    """Lightweight project entry from the projects registry file."""
    name: str
    path: str
    description: str
    tech: List[str]


@dataclass
class ProjectProfile:
    name: str
    path: str
    description: str
    tech_stack: List[str]
    key_features: List[str]
    languages: List[str]


@dataclass
class RankedProject:
    project: ProjectProfile
    relevance_score: float
    reasoning: str
    suggested_angle: str


@dataclass
class TailoredProject:
    name: str
    tech_stack_display: str
    bullet_points: List[str]


@dataclass
class TailoredResume:
    professional_summary: str
    projects: List[TailoredProject]
    infrastructure_and_tools: str = ""


@dataclass
class ResumeSection:
    name: str
    start_line: int
    end_line: int
    raw_content: str


@dataclass
class ExistingResume:
    preamble: str  # Everything before \begin{document}
    heading: str  # The heading/contact block
    summary: ResumeSection
    experience: ResumeSection
    projects: ResumeSection
    education: ResumeSection
    skills: ResumeSection
    postamble: str  # \end{document}
    raw_lines: List[str] = field(default_factory=list)
