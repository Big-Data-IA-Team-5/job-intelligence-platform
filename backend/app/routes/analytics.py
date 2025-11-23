"""
Analytics Routes
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyticsQuery
from app.utils.snowflake_client import get_snowflake_client

router = APIRouter()


@router.get("/companies")
async def top_companies(limit: int = 20):
    """Get top companies by job postings"""
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT 
            company_name,
            COUNT(*) as job_count,
            SUM(CASE WHEN likely_sponsors_h1b THEN 1 ELSE 0 END) as h1b_sponsor_count,
            SUM(CASE WHEN is_remote THEN 1 ELSE 0 END) as remote_count
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE posted_date >= CURRENT_DATE - 30
        GROUP BY company_name
        ORDER BY job_count DESC
        LIMIT %s
        """
        
        df = client.execute_query(query, [limit])
        return {"companies": df.to_dict('records')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends")
async def job_trends(days: int = 30):
    """Get job posting trends over time"""
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT 
            DATE_TRUNC('day', posted_date) as date,
            COUNT(*) as job_count,
            COUNT(DISTINCT company_name) as company_count
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE posted_date >= CURRENT_DATE - %s
        GROUP BY date
        ORDER BY date
        """
        
        df = client.execute_query(query, [days])
        return {"trends": df.to_dict('records')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def job_categories():
    """Get job distribution by category"""
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT 
            job_category,
            COUNT(*) as count,
            AVG(CASE WHEN likely_sponsors_h1b THEN 1.0 ELSE 0.0 END) as h1b_rate
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE posted_date >= CURRENT_DATE - 30
        GROUP BY job_category
        ORDER BY count DESC
        """
        
        df = client.execute_query(query)
        return {"categories": df.to_dict('records')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/locations")
async def top_locations(limit: int = 20):
    """Get top locations by job count"""
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT 
            location,
            COUNT(*) as job_count
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE posted_date >= CURRENT_DATE - 30
            AND location != 'Remote'
        GROUP BY location
        ORDER BY job_count DESC
        LIMIT %s
        """
        
        df = client.execute_query(query, [limit])
        return {"locations": df.to_dict('records')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
