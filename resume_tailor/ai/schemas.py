"""Pydantic schemas for structured LLM outputs across the pipeline."""

from pydantic import BaseModel
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


class SelectedProject(BaseModel):
    name: str
    source: str  # "existing" or "discovered"
    relevance_score: float
    reasoning: str
    suggested_angle: str


class MatchingResponse(BaseModel):
    selected_projects: List[SelectedProject]
    professional_summary: str
    infrastructure_and_tools: str


class BulletPointsResponse(BaseModel):
    display_name: str
    tech_stack_display: str
    bullet_points: List[str]
