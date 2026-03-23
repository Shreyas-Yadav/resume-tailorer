"""Pydantic schemas for structured LLM outputs across the pipeline."""

import re
from pydantic import BaseModel, Field, field_validator
from typing import List


class JobPostingResponse(BaseModel):
    title: str
    company: str
    responsibilities: List[str]
    required_qualifications: List[str]
    preferred_qualifications: List[str]
    tech_stack: List[str]


class ProjectProfileResponse(BaseModel):
    name: str
    description: str
    tech_stack: List[str]
    key_features: List[str]
    languages: List[str]


class RequirementBucketResponse(BaseModel):
    name: str
    evidence: List[str]


class EnrichedProjectResponse(BaseModel):
    name: str
    description: str
    tech: List[str]
    key_features: List[str]
    languages: List[str]
    architecture_signals: List[str]
    outcomes: List[str]
    explicit_metrics: List[str]
    evidence_summary: str
    requirement_tags: List[str]


class SelectedProject(BaseModel):
    name: str
    relevance_score: float
    reasoning: str
    suggested_angle: str


class MatchingResponse(BaseModel):
    selected_projects: List[SelectedProject]
    requirement_buckets: List[RequirementBucketResponse] = Field(default_factory=list)
    professional_summary: str
    languages: List[str] = Field(default_factory=list)
    infrastructure_and_tools: List[str] = Field(default_factory=list)
    coursework: List[str] = Field(default_factory=list)

    @field_validator("infrastructure_and_tools", "languages", "coursework", mode="before")
    @classmethod
    def strip_markdown_bold(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in re.sub(r"\*\*(.+?)\*\*", r"\1", v).split(",") if item.strip()]
        return v


class BulletPointsResponse(BaseModel):
    display_name: str
    tech_stack_display: str
    bullet_points: List[str]


class ExperienceEntryResponse(BaseModel):
    company: str
    role: str
    bullet_points: List[str]


class ExperienceTailoringResponse(BaseModel):
    entries: List[ExperienceEntryResponse]


class SkillsTailoringResponse(BaseModel):
    languages: List[str]
    infrastructure_and_tools: List[str]
    coursework: List[str]


class ReviewIssueResponse(BaseModel):
    severity: str
    message: str


class ResumeReviewResponse(BaseModel):
    passed: bool
    underfilled: bool = False
    missing_requirements: List[str] = Field(default_factory=list)
    duplicated_themes: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    trim_suggestions: List[str] = Field(default_factory=list)
    page_fill_recommendations: List[str] = Field(default_factory=list)
    issues: List[ReviewIssueResponse] = Field(default_factory=list)


class AdditionalBulletResponse(BaseModel):
    bullet_point: str


class LinkedInMessageResponse(BaseModel):
    message: str = Field(description="Full LinkedIn connect message, plain text only, no markdown.")

    @field_validator("message")
    @classmethod
    def strip_markdown(cls, v: str) -> str:
        v = re.sub(r"\*\*(.+?)\*\*", r"\1", v)
        v = re.sub(r"\*(.+?)\*", r"\1", v)
        return v.strip()
