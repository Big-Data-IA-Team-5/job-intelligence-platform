"""
Resume-related Pydantic models
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List

class ResumeProfile(BaseModel):
    """Extracted resume profile"""
    technical_skills: List[str]
    soft_skills: List[str]
    total_experience_years: float
    education_level: str
    work_authorization: str
    desired_roles: List[str]
    preferred_locations: List[str]
    salary_min: Optional[int] = None

class JobMatch(BaseModel):
    """Single job match"""
    job_id: str
    title: str
    company: str
    location: str
    overall_score: float
    skills_score: float
    experience_score: float
    visa_score: float
    location_score: float
    match_reasoning: str
    url: str
    visa_category: Optional[str] = None

class MatchRequest(BaseModel):
    """Resume matching request"""
    resume_text: str = Field(..., min_length=100, max_length=50000)
    user_id: Optional[str] = Field(None, max_length=100)

class MatchResponse(BaseModel):
    """Resume matching response"""
    status: str
    profile: ResumeProfile
    top_matches: List[JobMatch]
    total_candidates: int
    resume_id: str

class UploadRequest(BaseModel):
    """Resume upload request"""
    resume_text: str = Field(..., min_length=100, max_length=50000)
    file_name: str = Field(..., max_length=255)
    user_id: Optional[str] = None
    
    @validator('file_name')
    def validate_file_extension(cls, v):
        """Validate file extension"""
        if not v or '.' not in v:
            raise ValueError('Invalid filename: missing file extension')
        
        extension = v.lower().split('.')[-1]
        allowed = ['pdf', 'docx', 'txt']
        
        if extension not in allowed:
            raise ValueError(f'Invalid file type .{extension}. Allowed: {", ".join(allowed)}')
        
        return v

class FileUploadRequest(BaseModel):
    """File upload with binary content validation"""
    filename: str = Field(..., max_length=255)
    content: bytes = Field(...)
    user_id: Optional[str] = None

class UploadResponse(BaseModel):
    """Resume upload response"""
    status: str
    resume_id: str
    message: str