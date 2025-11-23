"""
Jobs Routes
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import SavedJobRequest
from app.utils.snowflake_client import get_snowflake_client

router = APIRouter()


@router.get("/{job_id}")
async def get_job(job_id: str, source: str):
    """Get detailed job information"""
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT *
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE job_id = %s AND source = %s
        """
        
        df = client.execute_query(query, [job_id, source])
        
        if df.empty:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return df.to_dict('records')[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save")
async def save_job(request: SavedJobRequest):
    """Save a job for a user"""
    try:
        client = get_snowflake_client()
        
        query = """
        INSERT INTO MARTS.USER_SAVED_JOBS (user_id, job_id, source, notes)
        VALUES (%s, %s, %s, %s)
        """
        
        client.execute_query(
            query, 
            [request.user_id, request.job_id, request.source, request.notes]
        )
        
        return {"message": "Job saved successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saved/{user_id}")
async def get_saved_jobs(user_id: str):
    """Get all saved jobs for a user"""
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT 
            s.job_id,
            s.source,
            s.saved_at,
            s.notes,
            j.title,
            j.company_name,
            j.location,
            j.url
        FROM MARTS.USER_SAVED_JOBS s
        JOIN MARTS.JOB_INTELLIGENCE_MART j
            ON s.job_id = j.job_id AND s.source = j.source
        WHERE s.user_id = %s
        ORDER BY s.saved_at DESC
        """
        
        df = client.execute_query(query, [user_id])
        
        return {"saved_jobs": df.to_dict('records')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/saved/{user_id}/{job_id}")
async def delete_saved_job(user_id: str, job_id: str, source: str):
    """Remove a saved job"""
    try:
        client = get_snowflake_client()
        
        query = """
        DELETE FROM MARTS.USER_SAVED_JOBS
        WHERE user_id = %s AND job_id = %s AND source = %s
        """
        
        client.execute_query(query, [user_id, job_id, source])
        
        return {"message": "Saved job removed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
