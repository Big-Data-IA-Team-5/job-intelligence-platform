"""
Analytics API routes
Provides statistics and insights about jobs, companies, and trends
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from app.utils.agent_wrapper import AgentManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


class TrendPoint(BaseModel):
    """Single trend data point"""
    date: str
    count: int


class CategoryStat(BaseModel):
    """Job category statistics"""
    category: str
    count: int
    percentage: float


class CompanyStat(BaseModel):
    """Company statistics"""
    company: str
    job_count: int
    h1b_sponsor: bool
    avg_approval_rate: Optional[float] = None
    h1b_applications: Optional[int] = None  # Total H-1B applications filed
    h1b_certified: Optional[int] = None  # Total H-1B applications approved/certified


class LocationStat(BaseModel):
    """Location statistics"""
    location: str
    job_count: int
    avg_salary: Optional[float] = None


class AnalyticsSummary(BaseModel):
    """Overall analytics summary"""
    total_jobs: int
    total_companies: int
    h1b_sponsors: int
    avg_salary: Optional[float] = None
    recent_postings_7d: int


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary():
    """
    Get overall platform statistics
    
    **Returns:**
    - Total jobs available
    - Number of companies
    - H-1B sponsors count
    - Average salary
    - Recent postings (last 7 days)
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        # Get overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(DISTINCT company) as total_companies,
                COUNT(DISTINCT CASE WHEN h1b_sponsor = TRUE THEN company END) as h1b_sponsors,
                AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary,
                COUNT(CASE WHEN days_since_posted <= 7 THEN 1 END) as recent_7d
            FROM jobs_processed
        """)
        
        row = cursor.fetchone()
        
        return AnalyticsSummary(
            total_jobs=row[0] or 0,
            total_companies=row[1] or 0,
            h1b_sponsors=row[2] or 0,
            avg_salary=float(row[3]) if row[3] else None,
            recent_postings_7d=row[4] or 0
        )
        
    except Exception as e:
        logger.error(f"Analytics summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/trends", response_model=List[TrendPoint])
async def get_job_trends(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get job posting trends over time
    
    **Parameters:**
    - days: Number of days to look back (1-365)
    
    **Returns:**
    - Daily job posting counts
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute(f"""
            SELECT 
                DATE(scraped_at) as posting_date,
                COUNT(*) as job_count
            FROM jobs_processed
            WHERE scraped_at >= DATEADD(day, -{days}, CURRENT_DATE())
            GROUP BY DATE(scraped_at)
            ORDER BY posting_date DESC
            LIMIT 100
        """)
        
        trends = []
        for row in cursor.fetchall():
            trends.append(TrendPoint(
                date=str(row[0]),
                count=row[1]
            ))
        
        return trends
        
    except Exception as e:
        logger.error(f"Trends error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/categories", response_model=List[CategoryStat])
async def get_category_distribution():
    """
    Get job distribution by visa category
    
    **Returns:**
    - Breakdown by CPT, OPT, H-1B, etc.
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute("""
            WITH total AS (
                SELECT COUNT(*) as total_count FROM jobs_processed
            )
            SELECT 
                COALESCE(visa_category, 'Unknown') as category,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / total.total_count, 2) as percentage
            FROM jobs_processed, total
            GROUP BY visa_category, total.total_count
            ORDER BY count DESC
        """)
        
        categories = []
        for row in cursor.fetchall():
            categories.append(CategoryStat(
                category=row[0],
                count=row[1],
                percentage=float(row[2])
            ))
        
        return categories
        
    except Exception as e:
        logger.error(f"Categories error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/companies", response_model=List[CompanyStat])
async def get_top_companies(
    limit: int = Query(default=20, ge=1, le=100, description="Number of companies to return")
):
    """
    Get top companies by job count
    
    **Parameters:**
    - limit: Number of companies to return (1-100)
    
    **Returns:**
    - Top companies with job counts and H-1B info
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute(f"""
            SELECT 
                j.company,
                COUNT(*) as job_count,
                MAX(j.h1b_sponsor) as h1b_sponsor,
                -- Calculate REAL approval rate: total_certified / total_filings
                MAX(e.total_certified * 100.0 / NULLIF(e.total_filings, 0)) as avg_approval_rate
            FROM jobs_processed j
            LEFT JOIN employer_intelligence e
                ON UPPER(j.company_clean) = e.employer_clean
            WHERE j.company IS NOT NULL
                AND j.company NOT IN ('United States', 'USA', 'US', 'International', 'INTERNATIONAL', 'Unknown', 'Confidential', 'N/A', 'Not Specified', 'Private')
                AND j.company NOT ILIKE 'international%'
                AND j.company NOT ILIKE 'unknown%'
                AND j.company NOT ILIKE 'confidential%'
                AND j.company NOT IN ('AR', 'BR', 'HI', 'CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI', 'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI', 'CO', 'MN', 'SC', 'AL', 'LA', 'KY', 'OR', 'OK', 'CT', 'UT', 'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI', 'NH', 'ME', 'MT', 'RI', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY')
                AND LENGTH(j.company) > 2
            GROUP BY j.company
            ORDER BY job_count DESC
            LIMIT {limit}
        """)
        
        companies = []
        for row in cursor.fetchall():
            companies.append(CompanyStat(
                company=row[0],
                job_count=row[1],
                h1b_sponsor=bool(row[2]),
                avg_approval_rate=float(row[3]) if row[3] else None
            ))
        
        return companies
        
    except Exception as e:
        logger.error(f"Companies error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/locations", response_model=List[LocationStat])
async def get_top_locations(
    limit: int = Query(default=15, ge=1, le=50, description="Number of locations to return")
):
    """
    Get top locations by job count
    
    **Parameters:**
    - limit: Number of locations to return (1-50)
    
    **Returns:**
    - Top locations with job counts and average salaries
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute(f"""
            SELECT 
                location,
                COUNT(*) as job_count,
                AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary
            FROM jobs_processed
            WHERE location IS NOT NULL 
                AND location != ''
                AND location NOT IN ('Hybrid', 'Remote', 'USA', 'US', 'United States')
                AND location NOT ILIKE '%remote%'
                AND location NOT ILIKE 'PACIFIC RIM%'
                AND location NOT ILIKE 'INTELLIGENT TECHNICAL%'
                AND LENGTH(location) > 2
            GROUP BY location
            ORDER BY job_count DESC
            LIMIT {limit}
        """)
        
        locations = []
        for row in cursor.fetchall():
            locations.append(LocationStat(
                location=row[0],
                job_count=row[1],
                avg_salary=float(row[2]) if row[2] else None
            ))
        
        return locations
        
    except Exception as e:
        logger.error(f"Locations error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/visa-sponsors", response_model=List[CompanyStat])
async def get_h1b_sponsors(
    limit: int = Query(default=50, ge=1, le=100, description="Number of sponsors to return")
):
    """
    Get top H-1B sponsoring companies
    
    **Parameters:**
    - limit: Number of companies to return (1-100)
    
    **Returns:**
    - Companies that sponsor H-1B with approval rates
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute(f"""
            SELECT 
                j.company,
                COUNT(*) as job_count,
                TRUE as h1b_sponsor,
                -- Calculate REAL approval rate: total_certified / total_filings
                MAX(e.total_certified * 100.0 / NULLIF(e.total_filings, 0)) as avg_approval_rate,
                MAX(e.total_filings) as h1b_applications,
                MAX(e.total_certified) as h1b_certified
            FROM jobs_processed j
            LEFT JOIN employer_intelligence e
                ON UPPER(j.company_clean) = e.employer_clean
            WHERE j.h1b_sponsor = TRUE
                AND j.company IS NOT NULL
                AND j.company NOT IN ('United States', 'USA', 'US', 'International', 'INTERNATIONAL', 'ICE', 'Unknown', 'Confidential', 'N/A', 'Not Specified', 'Private')
                AND j.company NOT ILIKE 'international%'
                AND j.company NOT ILIKE 'unknown%'
                AND j.company NOT ILIKE 'confidential%'
                AND j.company NOT IN ('AR', 'BR', 'HI', 'CA', 'NY', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC', 'MI', 'NJ', 'VA', 'WA', 'AZ', 'MA', 'TN', 'IN', 'MO', 'MD', 'WI', 'CO', 'MN', 'SC', 'AL', 'LA', 'KY', 'OR', 'OK', 'CT', 'UT', 'IA', 'NV', 'AR', 'MS', 'KS', 'NM', 'NE', 'WV', 'ID', 'HI', 'NH', 'ME', 'MT', 'RI', 'DE', 'SD', 'ND', 'AK', 'VT', 'WY')
                AND LENGTH(j.company) > 2
            GROUP BY j.company
            HAVING MAX(e.total_certified * 100.0 / NULLIF(e.total_filings, 0)) > 0
            ORDER BY job_count DESC, avg_approval_rate DESC
            LIMIT {limit}
        """)
        
        sponsors = []
        for row in cursor.fetchall():
            sponsors.append(CompanyStat(
                company=row[0],
                job_count=row[1],
                h1b_sponsor=True,
                avg_approval_rate=float(row[3]) if row[3] else None,
                h1b_applications=int(row[4]) if row[4] else None,
                h1b_certified=int(row[5]) if row[5] else None
            ))
        
        return sponsors
        
    except Exception as e:
        logger.error(f"H-1B sponsors error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/work-models")
async def get_work_models():
    """
    Get job distribution by work model (Remote, Hybrid, On-site)
    
    **Returns:**
    - Work model breakdown with counts and percentages
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute("""
            WITH total AS (
                SELECT COUNT(*) as total_count FROM jobs_processed
            ),
            work_stats AS (
                SELECT 
                    CASE 
                        WHEN UPPER(location) LIKE '%REMOTE%' THEN 'Remote'
                        WHEN UPPER(location) LIKE '%HYBRID%' THEN 'Hybrid'
                        ELSE 'On-site'
                    END as work_model,
                    COUNT(*) as count,
                    AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary
                FROM jobs_processed
                GROUP BY 
                    CASE 
                        WHEN UPPER(location) LIKE '%REMOTE%' THEN 'Remote'
                        WHEN UPPER(location) LIKE '%HYBRID%' THEN 'Hybrid'
                        ELSE 'On-site'
                    END
            )
            SELECT 
                work_model,
                count,
                ROUND(count * 100.0 / total.total_count, 1) as percentage,
                avg_salary
            FROM work_stats, total
            ORDER BY count DESC
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'work_model': row[0],
                'count': row[1],
                'percentage': float(row[2]),
                'avg_salary': float(row[3]) if row[3] else None
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Work models error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/location-salary")
async def get_location_salary(
    limit: int = Query(default=15, ge=1, le=50, description="Number of locations to return")
):
    """
    Get top cities with average salaries and H-1B friendliness
    
    **Parameters:**
    - limit: Number of cities to return (1-50)
    
    **Returns:**
    - Cities with average salary and H-1B sponsor percentage
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute(f"""
            SELECT 
                location as city,
                AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary,
                COUNT(*) as job_count,
                ROUND(COUNT(CASE WHEN h1b_sponsor = TRUE THEN 1 END) * 100.0 / COUNT(*), 1) as h1b_friendly_pct
            FROM jobs_processed
            WHERE location IS NOT NULL 
                AND location != ''
                AND location NOT IN ('Hybrid', 'Remote', 'USA', 'US', 'United States')
                AND location NOT ILIKE '%remote%'
                AND LENGTH(location) > 2
            GROUP BY location
            HAVING COUNT(*) >= 5
            ORDER BY job_count DESC, avg_salary DESC
            LIMIT {limit}
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'city': row[0],
                'avg_salary': float(row[1]) if row[1] else 0,
                'job_count': row[2],
                'h1b_friendly_pct': float(row[3]) if row[3] else 0
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Location salary error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/experience-level")
async def get_experience_levels():
    """
    Get job distribution by experience level
    
    **Returns:**
    - Experience level breakdown with counts and percentages
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute("""
            WITH total AS (
                SELECT COUNT(*) as total_count FROM jobs_processed
            ),
            exp_stats AS (
                SELECT 
                    CASE 
                        WHEN UPPER(title) LIKE '%INTERN%' OR UPPER(title) LIKE '%ENTRY%' THEN 'Entry Level'
                        WHEN UPPER(title) LIKE '%JUNIOR%' OR UPPER(title) LIKE '%ASSOCIATE%' THEN 'Junior'
                        WHEN UPPER(title) LIKE '%SENIOR%' OR UPPER(title) LIKE '%SR%' THEN 'Senior'
                        WHEN UPPER(title) LIKE '%LEAD%' OR UPPER(title) LIKE '%PRINCIPAL%' OR UPPER(title) LIKE '%STAFF%' THEN 'Lead/Principal'
                        ELSE 'Mid-Level'
                    END as level,
                    COUNT(*) as job_count,
                    AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary
                FROM jobs_processed
                GROUP BY level
            )
            SELECT 
                level,
                job_count,
                ROUND(job_count * 100.0 / total.total_count, 1) as percentage,
                avg_salary
            FROM exp_stats, total
            ORDER BY 
                CASE level
                    WHEN 'Entry Level' THEN 1
                    WHEN 'Junior' THEN 2
                    WHEN 'Mid-Level' THEN 3
                    WHEN 'Senior' THEN 4
                    WHEN 'Lead/Principal' THEN 5
                END
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'level': row[0],
                'job_count': row[1],
                'percentage': float(row[2]),
                'avg_salary': float(row[3]) if row[3] else None
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Experience levels error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/salary-by-role")
async def get_salary_by_role(
    limit: int = Query(default=20, ge=1, le=50, description="Number of roles to return")
):
    """
    Get average salary by job role/category
    
    **Parameters:**
    - limit: Number of roles to return (1-50)
    
    **Returns:**
    - Job roles with average salaries and job counts
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        cursor.execute(f"""
            WITH role_categories AS (
                SELECT 
                    CASE 
                        WHEN UPPER(title) LIKE '%DATA SCIEN%' OR UPPER(title) LIKE '%ML%' OR UPPER(title) LIKE '%MACHINE LEARN%' THEN 'Data Scientist'
                        WHEN UPPER(title) LIKE '%DATA ENG%' THEN 'Data Engineer'
                        WHEN UPPER(title) LIKE '%DATA ANALY%' OR UPPER(title) LIKE '%BUSINESS ANALY%' THEN 'Data Analyst'
                        WHEN UPPER(title) LIKE '%SOFTWARE ENG%' OR UPPER(title) LIKE '%DEVELOPER%' OR UPPER(title) LIKE '%PROGRAMMER%' THEN 'Software Engineer'
                        WHEN UPPER(title) LIKE '%DEVOPS%' OR UPPER(title) LIKE '%SRE%' OR UPPER(title) LIKE '%SITE RELIABILITY%' THEN 'DevOps/SRE'
                        WHEN UPPER(title) LIKE '%CLOUD%' THEN 'Cloud Engineer'
                        WHEN UPPER(title) LIKE '%FULL STACK%' THEN 'Full Stack Developer'
                        WHEN UPPER(title) LIKE '%FRONT%END%' OR UPPER(title) LIKE '%UI%' THEN 'Frontend Developer'
                        WHEN UPPER(title) LIKE '%BACK%END%' THEN 'Backend Developer'
                        WHEN UPPER(title) LIKE '%SECURITY%' OR UPPER(title) LIKE '%CYBER%' THEN 'Security Engineer'
                        WHEN UPPER(title) LIKE '%QA%' OR UPPER(title) LIKE '%TEST%' THEN 'QA/Test Engineer'
                        WHEN UPPER(title) LIKE '%PRODUCT MANAGER%' OR UPPER(title) LIKE '%PM%' THEN 'Product Manager'
                        ELSE 'Other Tech Role'
                    END as role,
                    salary_min
                FROM jobs_processed
            )
            SELECT 
                role,
                ROUND(AVG(CASE WHEN salary_min > 0 THEN salary_min END), 0) as avg_salary,
                COUNT(*) as job_count
            FROM role_categories
            GROUP BY role
            HAVING COUNT(*) >= 5
            ORDER BY job_count DESC, avg_salary DESC
            LIMIT {limit}
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'role': row[0],
                'avg_salary': float(row[1]) if row[1] else 0,
                'job_count': row[2]
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Salary by role error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/top-skills")
async def get_top_skills(
    limit: int = Query(default=20, ge=1, le=50, description="Number of skills to return")
):
    """
    Get most in-demand skills across all job postings
    
    **Parameters:**
    - limit: Number of skills to return (1-50)
    
    **Returns:**
    - Top skills with counts
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()
        
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")
        
        # Extract skills from job descriptions and titles
        cursor.execute(f"""
            WITH skill_keywords AS (
                SELECT 
                    UPPER(value) as skill
                FROM jobs_processed,
                LATERAL FLATTEN(
                    input => SPLIT(
                        REGEXP_REPLACE(
                            UPPER(COALESCE(description, '') || ' ' || COALESCE(title, '')),
                            '[^A-Z0-9+ ]', ' '
                        ),
                        ' '
                    )
                )
                WHERE LENGTH(value) > 2
            ),
            common_skills AS (
                SELECT DISTINCT skill_name FROM (
                    VALUES 
                        ('PYTHON'), ('JAVA'), ('JAVASCRIPT'), ('SQL'), ('AWS'), 
                        ('AZURE'), ('GCP'), ('REACT'), ('NODE'), ('DOCKER'),
                        ('KUBERNETES'), ('TENSORFLOW'), ('PYTORCH'), ('SPARK'),
                        ('HADOOP'), ('KAFKA'), ('REDIS'), ('MONGODB'), ('POSTGRES'),
                        ('C++'), ('GOLANG'), ('RUST'), ('TYPESCRIPT'), ('VUE'),
                        ('ANGULAR'), ('DJANGO'), ('FLASK'), ('SPRING'), ('JENKINS'),
                        ('TERRAFORM'), ('ANSIBLE'), ('GIT'), ('LINUX'), ('TABLEAU'),
                        ('POWERBI'), ('EXCEL'), ('R'), ('SCALA'), ('SWIFT'),
                        ('KOTLIN'), ('PHP'), ('RUBY'), ('PERL'), ('BASH'),
                        ('MATLAB'), ('SAS'), ('SPSS'), ('HADOOP'), ('HIVE'),
                        ('AIRFLOW'), ('DATABRICKS'), ('SNOWFLAKE'), ('REDSHIFT'),
                        ('BIGQUERY'), ('LOOKER'), ('GRAFANA'), ('PROMETHEUS'),
                        ('ELASTICSEARCH'), ('CASSANDRA'), ('DYNAMODB'), ('NEO4J'),
                        ('GRAPHQL'), ('REST'), ('API'), ('MICROSERVICES'), ('AGILE'),
                        ('SCRUM'), ('DEVOPS'), ('CICD'), ('ML'), ('AI'),
                        ('NLP'), ('COMPUTER VISION'), ('DEEP LEARNING'), ('ETL')
                ) AS t(skill_name)
            )
            SELECT 
                cs.skill_name as skill,
                COUNT(DISTINCT sk.skill) as count
            FROM common_skills cs
            LEFT JOIN skill_keywords sk ON sk.skill = cs.skill_name
            GROUP BY cs.skill_name
            HAVING COUNT(DISTINCT sk.skill) > 0
            ORDER BY count DESC
            LIMIT {limit}
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'skill': row[0],
                'count': row[1]
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Top skills error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()
