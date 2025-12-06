"""
Job-related Pydantic models
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date

class JobResponse(BaseModel):
    """Single job response with H-1B data"""
    job_id: str
    url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    job_type: Optional[str] = None
    visa_category: Optional[str] = None
    h1b_sponsor: Optional[bool] = None
    days_since_posted: Optional[int] = None
    
    # Enhanced fields
    work_model: Optional[str] = None
    department: Optional[str] = None
    company_size: Optional[str] = None
    h1b_sponsored_explicit: Optional[bool] = None
    is_new_grad_role: Optional[bool] = None
    job_category: Optional[str] = None
    
    # H-1B data from h1b_raw table
    total_petitions: Optional[int] = None
    avg_approval_rate: Optional[float] = None
    h1b_employer_name: Optional[str] = None
    
    # Additional metadata
    snippet: Optional[str] = None
    posted_date: Optional[date] = None
    relevance_score: Optional[int] = None
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    """Job search request"""
    query: str = Field(..., min_length=2, max_length=500, description="Search query")
    visa_status: Optional[str] = Field(None, description="CPT, OPT, H-1B, US-Only")
    location: Optional[str] = Field(None, max_length=100)
    salary_min: Optional[int] = Field(None, ge=0, le=1000000)
    job_type: Optional[str] = None
    limit: int = Field(20, ge=1, le=100)
    
    @validator('visa_status')
    def validate_visa_status(cls, v):
        if v and v not in ['CPT', 'OPT', 'H-1B', 'US-Only']:
            raise ValueError('Must be CPT, OPT, H-1B, or US-Only')
        return v

class SearchResponse(BaseModel):
    """Job search response"""
    status: str
    query: str
    total: int
    jobs: List[JobResponse]
    sql: Optional[str] = None  # For debugging

class ClassifyRequest(BaseModel):
    """Visa classification request"""
    title: str = Field(..., min_length=2, max_length=200)
    company: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10, max_length=10000)

class ClassifyResponse(BaseModel):
    """Visa classification response"""
    visa_category: str
    confidence: float
    signals: List[str]
    reasoning: str
    needs_review: bool