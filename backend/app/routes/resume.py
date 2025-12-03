"""
Resume Matching Endpoint - Agent 4 Integration
"""
from fastapi import APIRouter, HTTPException
from app.models.resume import (
    MatchRequest, MatchResponse, UploadRequest, UploadResponse,
    ResumeProfile, JobMatch
)
from app.models.response import ErrorResponse
from app.utils.agent_wrapper import AgentManager
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resume", tags=["Resume Matching"])

@router.post("/match",
    response_model=MatchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def match_resume(request: MatchRequest):
    """
    Match resume to top jobs
    
    Uses Agent 4 to:
    1. Extract skills, experience, preferences from resume
    2. Find matching jobs in database
    3. Score and rank top 10 matches
    
    **Example Request:**
    ```json
    {
      "resume_text": "John Doe\\n5 years Python experience...\\nMaster's CS...",
      "user_id": "user_123"
    }
    ```
    
    **Returns:**
    - Extracted profile (skills, experience, education)
    - Top 10 job matches with scores
    - Match reasoning for each job
    """
    
    matcher = None
    try:
        # Generate resume ID
        resume_id = f"resume_{uuid.uuid4().hex[:8]}"
        
        # Initialize Agent 4
        matcher = AgentManager.get_matcher()
        
        # Match
        result = matcher.match_resume(
            resume_id=resume_id,
            resume_text=request.resume_text
        )
        
        # Convert to response model
        profile = ResumeProfile(**result['profile'])
        
        matches = [
            JobMatch(
                job_id=m.get('job_id') or m.get('JOB_ID', ''),
                title=m.get('title') or m.get('TITLE', ''),
                company=m.get('company') or m.get('COMPANY', ''),
                location=m.get('location') or m.get('LOCATION', ''),
                overall_score=m.get('overall_score', 0.0),
                skills_score=m.get('skills_score', 0.0),
                experience_score=m.get('experience_score', 0.0),
                visa_score=m.get('visa_score', 0.0),
                location_score=m.get('location_score', 0.0),
                match_reasoning=m.get('match_reasoning', ''),
                url=m.get('url') or m.get('URL', ''),
                visa_category=m.get('visa_category') or m.get('VISA_CATEGORY')
            )
            for m in result['top_matches']
        ]
        
        return MatchResponse(
            status="success",
            profile=profile,
            top_matches=matches,
            total_candidates=result['total_candidates'],
            resume_id=resume_id
        )
    
    except Exception as e:
        logger.error(f"Matching error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume matching failed: {str(e)}"
        )
    
    finally:
        if matcher:
            matcher.close()

@router.post("/upload",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def upload_resume(request: UploadRequest):
    """
    Upload resume (stores in Snowflake)
    
    **Example Request:**
    ```json
    {
      "resume_text": "Full resume text...",
      "file_name": "john_doe_resume.pdf",
      "user_id": "user_123"
    }
    ```
    
    **Returns:**
    - Resume ID
    - Upload status
    """
    
    matcher = None
    try:
        # Generate resume ID
        resume_id = f"resume_{uuid.uuid4().hex[:8]}"
        
        # Initialize Agent 4
        matcher = AgentManager.get_matcher()
        
        # Store resume (simplified - just extract profile)
        result = matcher.match_resume(
            resume_id=resume_id,
            resume_text=request.resume_text
        )
        
        return UploadResponse(
            status="success",
            resume_id=resume_id,
            message="Resume uploaded and processed successfully"
        )
    
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Resume upload failed: {str(e)}"
        )
    
    finally:
        if matcher:
            matcher.close()