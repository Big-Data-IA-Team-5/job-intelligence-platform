"""
Pydantic Schemas for API requests/responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class JobBase(BaseModel):
    """Base job schema"""
    job_id: str
    source: str
    title: str
    company_name: str
    location: str
    description: str
    posted_date: datetime
    url: str


class JobDetail(JobBase):
    """Detailed job schema with enrichment"""
    job_type: Optional[str] = None
    salary_range: Optional[str] = None
    seniority_level: Optional[str] = None
    job_category: Optional[str] = None
    extracted_skills: Optional[str] = None
    is_remote: bool = False
    likely_sponsors_h1b: bool = False
    h1b_employer_name: Optional[str] = None
    h1b_application_count: Optional[int] = None
    prevailing_wage: Optional[float] = None


class JobSearchRequest(BaseModel):
    """Job search request"""
    query: str = Field(..., description="Search query")
    location: Optional[str] = Field(None, description="Location filter")
    is_remote: Optional[bool] = Field(None, description="Remote jobs only")
    sponsors_h1b: Optional[bool] = Field(None, description="H1B sponsorship filter")
    job_category: Optional[str] = Field(None, description="Job category")
    seniority_level: Optional[str] = Field(None, description="Seniority level")
    limit: int = Field(20, ge=1, le=100, description="Number of results")


class JobSearchResponse(BaseModel):
    """Job search response"""
    jobs: List[JobDetail]
    total_count: int
    query: str


class ResumeUploadRequest(BaseModel):
    """Resume upload request"""
    user_id: str
    resume_text: str


class ResumeMatchRequest(BaseModel):
    """Resume matching request"""
    resume_id: str
    top_k: int = Field(10, ge=1, le=50)
    min_similarity: float = Field(0.7, ge=0.0, le=1.0)


class JobMatch(BaseModel):
    """Job match with similarity score"""
    job: JobDetail
    similarity_score: float


class ResumeMatchResponse(BaseModel):
    """Resume matching response"""
    matches: List[JobMatch]
    resume_id: str


class SavedJobRequest(BaseModel):
    """Save job request"""
    user_id: str
    job_id: str
    source: str
    notes: Optional[str] = None


class AnalyticsQuery(BaseModel):
    """Analytics query parameters"""
    metric: str = Field(..., description="Metric to query: companies, locations, categories, trends")
    filters: Optional[dict] = None
    limit: int = Field(20, ge=1, le=100)
