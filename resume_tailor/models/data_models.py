"""Data models for the resume tailor pipeline."""

from dataclasses import dataclass, field
from typing import List


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
    key_features: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    repo_url: str = ""
    demo_url: str = ""
    impact_signals: List[str] = field(default_factory=list)


@dataclass
class RequirementBucket:
    name: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class EnrichedProject:
    name: str
    path: str
    description: str
    tech: List[str]
    key_features: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    architecture_signals: List[str] = field(default_factory=list)
    outcomes: List[str] = field(default_factory=list)
    explicit_metrics: List[str] = field(default_factory=list)
    evidence_summary: str = ""
    requirement_tags: List[str] = field(default_factory=list)
    workflow_signals: List[str] = field(default_factory=list)
    automation_signals: List[str] = field(default_factory=list)
    result_signals: List[str] = field(default_factory=list)
    repo_url: str = ""
    demo_url: str = ""


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
    repo_url: str = ""
    demo_url: str = ""


@dataclass
class TailoredExperienceEntry:
    company: str
    role: str
    bullet_points: List[str]


@dataclass
class TailoredSkills:
    languages: List[str] = field(default_factory=list)
    infrastructure_and_tools: List[str] = field(default_factory=list)
    coursework: List[str] = field(default_factory=list)


@dataclass
class ReviewIssue:
    severity: str
    message: str


@dataclass
class ResumeReview:
    passed: bool
    underfilled: bool = False
    generic_summary: bool = False
    shallow_ai_positioning: bool = False
    weak_experience_framing: bool = False
    missing_requirements: List[str] = field(default_factory=list)
    duplicated_themes: List[str] = field(default_factory=list)
    unsupported_claims: List[str] = field(default_factory=list)
    trim_suggestions: List[str] = field(default_factory=list)
    page_fill_recommendations: List[str] = field(default_factory=list)
    credibility_gaps: List[str] = field(default_factory=list)
    issues: List[ReviewIssue] = field(default_factory=list)


@dataclass
class TailoredResume:
    professional_summary: str
    projects: List[TailoredProject]
    experience: List[TailoredExperienceEntry] = field(default_factory=list)
    skills: TailoredSkills = field(default_factory=TailoredSkills)
    review: ResumeReview = field(default_factory=lambda: ResumeReview(passed=True))


@dataclass
class ResumeSection:
    name: str
    start_line: int
    end_line: int
    raw_content: str


@dataclass
class ExistingExperienceEntry:
    company: str
    role: str
    header_tex: str
    bullets: List[str]


@dataclass
class ExistingSkills:
    languages: List[str] = field(default_factory=list)
    infrastructure_and_tools: List[str] = field(default_factory=list)
    coursework: List[str] = field(default_factory=list)


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
