"""
Search Routes
"""
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import JobSearchRequest, JobSearchResponse, JobDetail
from app.utils.snowflake_client import get_snowflake_client
from typing import Optional

router = APIRouter()


@router.post("/", response_model=JobSearchResponse)
async def search_jobs(request: JobSearchRequest):
    """
    Search for jobs using semantic search or filters
    """
    try:
        client = get_snowflake_client()
        
        # Build query based on request
        query = """
        SELECT 
            job_id, source, title, company_name, location, description,
            posted_date, url, job_type, salary_range, seniority_level,
            job_category, extracted_skills, is_remote, likely_sponsors_h1b,
            h1b_employer_name, h1b_application_count, prevailing_wage
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if request.location:
            query += " AND LOWER(location) LIKE LOWER(%s)"
            params.append(f"%{request.location}%")
        
        if request.is_remote is not None:
            query += " AND is_remote = %s"
            params.append(request.is_remote)
        
        if request.sponsors_h1b is not None:
            query += " AND likely_sponsors_h1b = %s"
            params.append(request.sponsors_h1b)
        
        if request.job_category:
            query += " AND job_category = %s"
            params.append(request.job_category)
        
        if request.seniority_level:
            query += " AND seniority_level = %s"
            params.append(request.seniority_level)
        
        # Text search
        if request.query:
            query += """ AND (
                LOWER(title) LIKE LOWER(%s) 
                OR LOWER(description) LIKE LOWER(%s)
                OR LOWER(extracted_skills) LIKE LOWER(%s)
            )"""
            search_term = f"%{request.query}%"
            params.extend([search_term, search_term, search_term])
        
        query += " ORDER BY posted_date DESC LIMIT %s"
        params.append(request.limit)
        
        # Execute query
        df = client.execute_query(query, params)
        
        jobs = [JobDetail(**row) for row in df.to_dict('records')]
        
        return JobSearchResponse(
            jobs=jobs,
            total_count=len(jobs),
            query=request.query
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic", response_model=JobSearchResponse)
async def semantic_search(
    query: str = Query(..., description="Semantic search query"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Semantic search using vector similarity
    """
    try:
        client = get_snowflake_client()
        
        # Generate embedding for query
        embed_query = f"""
        SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', %s) AS query_embedding
        """
        
        embedding_df = client.execute_query(embed_query, [query])
        query_embedding = embedding_df['QUERY_EMBEDDING'].iloc[0]
        
        # Search using vector similarity
        search_query = """
        SELECT 
            job_id, source, title, company_name, location, description,
            posted_date, url, job_type, salary_range, seniority_level,
            job_category, extracted_skills, is_remote, likely_sponsors_h1b,
            h1b_employer_name, h1b_application_count, prevailing_wage,
            VECTOR_COSINE_SIMILARITY(description_embedding, %s) AS similarity
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE posted_date >= CURRENT_DATE - 60
        ORDER BY similarity DESC
        LIMIT %s
        """
        
        df = client.execute_query(search_query, [query_embedding, limit])
        
        jobs = [JobDetail(**row) for row in df.to_dict('records')]
        
        return JobSearchResponse(
            jobs=jobs,
            total_count=len(jobs),
            query=query
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
