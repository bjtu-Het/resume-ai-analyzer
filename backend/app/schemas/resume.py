from typing import Any, Optional

from pydantic import BaseModel, Field


class EducationItem(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    period: str = ""


class ProjectItem(BaseModel):
    name: str = ""
    role: str = ""
    description: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    period: str = ""


class ResumeProfile(BaseModel):
    name: str = ""
    phone: str = ""
    email: str = ""
    address: str = ""
    job_intention: str = ""
    expected_salary: str = ""
    work_years: Optional[float] = None
    education: list[EducationItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)


class JobKeywords(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    summary: str = ""
    required_skills: list[str] = Field(default_factory=list)
    required_years: Optional[float] = None
    required_education: str = ""


class MatchResult(BaseModel):
    score: float = 0
    skill_match_rate: float = 0
    experience_relevance: float = 0
    ai_score: Optional[float] = None
    reasons: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    resume_id: str = ""
    page_count: int = 0
    raw_text: str = ""
    cleaned_text: str = ""
    profile: ResumeProfile = Field(default_factory=ResumeProfile)


class AnalyzeResult(ParseResult):
    job: JobKeywords = Field(default_factory=JobKeywords)
    match: MatchResult = Field(default_factory=MatchResult)


class MatchRequest(BaseModel):
    job_description: str = Field(..., min_length=1)
    resume_text: str = ""
    profile: Optional[ResumeProfile] = None
    resume_id: str = ""
