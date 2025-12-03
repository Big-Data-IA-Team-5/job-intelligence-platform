"""
Job Search Endpoint - Agent 1 Integration
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.models.job import SearchResponse, JobResponse
from app.models.response import ErrorResponse
from app.utils.agent_wrapper import AgentManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Job Search"])

@router.get("/search", 
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    })
async def search_jobs(
    query: str = Query(..., min_length=2, max_length=500, description="Search query"),
    visa_status: Optional[str] = Query(None, description="CPT, OPT, H-1B, US-Only"),
    location: Optional[str] = Query(None, max_length=100, description="City or state"),
    salary_min: Optional[int] = Query(None, ge=0, le=1000000, description="Minimum salary"),
    job_type: Optional[str] = Query(None, description="Internship, Full-time, etc."),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Search jobs using natural language
    
    **Examples:**
    - `/api/search?query=CPT internships in Boston`
    - `/api/search?query=data engineer&salary_min=80000`
    - `/api/search?query=software engineer&visa_status=H-1B`
    
    **Parameters:**
    - **query**: Natural language search (required)
    - **visa_status**: Filter by visa eligibility
    - **location**: Filter by location
    - **salary_min**: Minimum salary in USD
    - **job_type**: Filter by job type
    - **limit**: Number of results (max 100)
    
    **Returns:**
    - List of matching jobs
    - Total count
    - Query details
    """
    
    # Validate inputs
    if visa_status and visa_status not in ['CPT', 'OPT', 'H-1B', 'US-Only']:
        raise HTTPException(
            status_code=400,
            detail="visa_status must be CPT, OPT, H-1B, or US-Only"
        )
    
    agent = None
    try:
        # Initialize Agent 1
        agent = AgentManager.get_search_agent()
        
        # Build filters
        filters = {}
        if visa_status:
            filters['visa_status'] = visa_status
        if location:
            filters['location'] = location
        if salary_min:
            filters['salary_min'] = salary_min
        if job_type:
            filters['job_type'] = job_type
        filters['limit'] = limit
        
        # Search
        result = agent.search(query, filters)
        
        # Check result
        if result['status'] == 'error':
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Search failed')
            )
        
        # Convert to response model
        jobs = [
            JobResponse(
                job_id=job.get('JOB_ID'),
                url=job.get('URL'),
                title=job.get('TITLE'),
                company=job.get('COMPANY'),
                location=job.get('LOCATION'),
                description=job.get('DESCRIPTION'),
                salary_min=job.get('SALARY_MIN'),
                salary_max=job.get('SALARY_MAX'),
                job_type=job.get('JOB_TYPE'),
                visa_category=job.get('VISA_CATEGORY'),
                h1b_sponsor=job.get('H1B_SPONSOR'),
                days_since_posted=job.get('DAYS_SINCE_POSTED'),
                work_model=job.get('WORK_MODEL'),
                department=job.get('DEPARTMENT'),
                company_size=job.get('COMPANY_SIZE'),
                h1b_sponsored_explicit=job.get('H1B_SPONSORED_EXPLICIT'),
                is_new_grad_role=job.get('IS_NEW_GRAD_ROLE')
            )
            for job in result.get('jobs', [])
        ]
        
        return SearchResponse(
            status="success",
            query=result['query'],
            total=result['total'],
            jobs=jobs,
            sql=result.get('sql')  # For debugging
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
    
    finally:
        if agent:
            agent.close()