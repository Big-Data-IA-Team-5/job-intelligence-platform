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
    salary_max: Optional[int] = Query(None, ge=0, le=1000000, description="Maximum salary"),
    job_type: Optional[str] = Query(None, description="Internship, Full-time, etc."),
    work_model: Optional[str] = Query(None, description="Remote, Hybrid, On-site"),
    job_category: Optional[str] = Query(None, description="Engineering, Data, Product, etc."),
    h1b_sponsor: Optional[bool] = Query(None, description="Filter for H-1B sponsors"),
    min_approval_rate: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum H-1B approval rate"),
    min_petitions: Optional[int] = Query(None, ge=0, description="Minimum total H-1B petitions"),
    new_grad_only: Optional[bool] = Query(None, description="Entry level / new grad roles only"),
    company_size: Optional[str] = Query(None, description="Company size category"),
    limit: int = Query(20, ge=1, le=100, description="Number of results")
):
    """
    Search jobs using natural language with enhanced H-1B filtering
    
    **Examples:**
    - `/api/search?query=CPT internships in Boston`
    - `/api/search?query=data engineer&salary_min=80000&h1b_sponsor=true`
    - `/api/search?query=software engineer&visa_status=H-1B&min_approval_rate=0.8`
    - `/api/search?query=entry level jobs&new_grad_only=true`
    
    **Parameters:**
    - **query**: Natural language search (required)
    - **visa_status**: Filter by visa eligibility (CPT, OPT, H-1B, US-Only)
    - **location**: Filter by location
    - **salary_min**: Minimum salary in USD
    - **salary_max**: Maximum salary in USD
    - **job_type**: Filter by job type
    - **work_model**: Remote, Hybrid, or On-site
    - **job_category**: Engineering, Data, Product, Design, Sales, Marketing, Operations
    - **h1b_sponsor**: Filter for H-1B sponsors only
    - **min_approval_rate**: Minimum H-1B approval rate (0.0-1.0)
    - **min_petitions**: Minimum total H-1B petitions filed
    - **new_grad_only**: Entry level / new grad roles only
    - **company_size**: Company size category
    - **limit**: Number of results (max 100)
    
    **Returns:**
    - List of matching jobs with H-1B data
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
        if salary_max:
            filters['salary_max'] = salary_max
        if job_type:
            filters['job_type'] = job_type
        if work_model:
            filters['work_model'] = work_model
        if job_category:
            filters['job_category'] = job_category
        if h1b_sponsor is not None:
            filters['h1b_sponsor'] = h1b_sponsor
        if min_approval_rate is not None:
            filters['min_approval_rate'] = min_approval_rate
        if min_petitions is not None:
            filters['min_petitions'] = min_petitions
        if new_grad_only is not None:
            filters['new_grad_only'] = new_grad_only
        if company_size:
            filters['company_size'] = company_size
        filters['limit'] = limit
        
        # Search
        result = agent.search(query, filters)
        
        # Check result
        if result['status'] == 'error':
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Search failed')
            )
        
        # Convert to response model with H-1B data
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
                is_new_grad_role=job.get('IS_NEW_GRAD_ROLE'),
                job_category=job.get('JOB_CATEGORY'),
                # H-1B data from h1b_raw table
                total_petitions=job.get('TOTAL_PETITIONS'),
                avg_approval_rate=job.get('AVG_APPROVAL_RATE'),
                snippet=job.get('SNIPPET'),
                posted_date=job.get('POSTED_DATE'),
                relevance_score=job.get('RELEVANCE_SCORE')
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