"""
Jobs API routes
Provides job search, filtering, and database access
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date
import logging
import re
import json

from app.utils.agent_wrapper import AgentManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobFilters(BaseModel):
    """Job search filters"""
    search: Optional[str] = None
    companies: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    work_models: Optional[List[str]] = None
    experience_levels: Optional[List[str]] = None
    visa_sponsorship: Optional[str] = None  # "All", "Yes", "No"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    posted_within_days: Optional[int] = None  # 1, 7, 30
    job_types: Optional[List[str]] = None
    sort_by: Optional[str] = "most_recent"  # most_recent, highest_salary, company_az, h1b_rate
    limit: Optional[int] = 50  # Number of results to return (default 50, max 500)


class JobsResponse(BaseModel):
    """Jobs response with metadata"""
    jobs: List[Dict[str, Any]]
    total: int
    filters_applied: Dict[str, Any]


@router.post("/search", response_model=JobsResponse)
async def search_jobs(filters: JobFilters = Body(...)):
    """
    Search jobs with advanced filtering

    **Filters:**
    - search: Keyword search in title, company, description
    - companies: Filter by specific companies
    - locations: Filter by locations
    - work_models: Remote, Hybrid, On-site
    - experience_levels: Entry, Mid, Senior, Staff
    - visa_sponsorship: Filter by H-1B sponsorship (Yes/No/All)
    - salary_min/max: Salary range filter
    - posted_within_days: Filter by recency (1, 7, 30 days)
    - job_types: Full-time, Internship, Contract, etc.
    - sort_by: Sort order (most_recent, highest_salary, company_az, h1b_rate)

    **Returns:**
    - jobs: List of job objects with all fields
    - total: Total count of matching jobs
    - filters_applied: Summary of filters used
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()

        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")

        # Build WHERE clauses
        where_clauses = []

        # Search query
        if filters.search:
            search_term = filters.search.replace("'", "''")
            where_clauses.append(f"""
                (LOWER(title) LIKE LOWER('%{search_term}%')
                 OR LOWER(company) LIKE LOWER('%{search_term}%')
                 OR LOWER(description) LIKE LOWER('%{search_term}%')
                 OR LOWER(snippet) LIKE LOWER('%{search_term}%'))
            """)

        # Company filter
        if filters.companies and len(filters.companies) > 0:
            companies_str = "', '".join([c.replace("'", "''") for c in filters.companies])
            where_clauses.append(f"company IN ('{companies_str}')")

        # Location filter
        if filters.locations and len(filters.locations) > 0:
            location_conditions = []
            for loc in filters.locations:
                loc_clean = loc.replace("'", "''")
                location_conditions.append(f"LOWER(location) LIKE LOWER('%{loc_clean}%')")
            where_clauses.append(f"({' OR '.join(location_conditions)})")

        # Work model filter
        if filters.work_models and len(filters.work_models) > 0:
            models_str = "', '".join([m.replace("'", "''") for m in filters.work_models])
            where_clauses.append(f"work_model IN ('{models_str}')")

        # Visa sponsorship filter
        if filters.visa_sponsorship and filters.visa_sponsorship != "All":
            if filters.visa_sponsorship == "Yes":
                where_clauses.append("h1b_sponsor = TRUE")
            else:
                where_clauses.append("(h1b_sponsor = FALSE OR h1b_sponsor IS NULL)")

        # Salary filter - handle NULL values properly
        if filters.salary_min and filters.salary_min > 0:
            where_clauses.append(f"(salary_min >= {filters.salary_min} OR salary_max >= {filters.salary_min})")
        if filters.salary_max and filters.salary_max < 500000:
            where_clauses.append(f"(salary_max <= {filters.salary_max} OR (salary_max IS NULL AND salary_min <= {filters.salary_max}))")

        # Posted date filter
        if filters.posted_within_days:
            where_clauses.append(f"posted_date >= DATEADD(day, -{filters.posted_within_days}, CURRENT_DATE())")

        # Job type filter
        if filters.job_types and len(filters.job_types) > 0:
            types_str = "', '".join([t.replace("'", "''") for t in filters.job_types])
            where_clauses.append(f"job_type IN ('{types_str}')")

        # Use LLM to enhance search query with semantic understanding
        if filters.search and len(filters.search) > 3:
            try:
                search_escaped = filters.search.replace("'", "''")
                semantic_prompt = f"""Analyze this job search query and extract key concepts:

QUERY: "{filters.search}"

Provide:
1. Job titles (e.g., "software engineer" → ["Software Engineer", "SWE", "Developer"])
2. Skills/technologies (e.g., "python" → ["Python", "Django", "Flask"])
3. Related keywords

Respond with JSON:
{{
  "titles": ["title1", "title2"],
  "skills": ["skill1", "skill2"],
  "keywords": ["word1", "word2"]
}}

Be concise, max 5 items per category."""

                prompt_escaped = semantic_prompt.replace("'", "''")
                semantic_sql = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'mistral-large2',
                        '{prompt_escaped}'
                    )
                """
                cursor.execute(semantic_sql)
                semantic_response = cursor.fetchone()[0]

                # Parse and enhance query
                json_match = re.search(r'\{.*?\}', semantic_response, re.DOTALL)
                if json_match:
                    semantic_data = json.loads(json_match.group(0))
                    all_terms = (
                        semantic_data.get('titles', []) +
                        semantic_data.get('skills', []) +
                        semantic_data.get('keywords', [])
                    )
                    if all_terms:
                        search_conditions = []
                        for term in all_terms[:8]:
                            term_escaped = term.replace("'", "''")
                            search_conditions.append(f"LOWER(title) LIKE LOWER('%{term_escaped}%')")
                        enhanced_search = " OR ".join(search_conditions)
                        # Replace original search clause with enhanced version
                        if where_clauses and "LOWER(title) LIKE" in where_clauses[0]:
                            where_clauses[0] = f"({enhanced_search})"
                            logger.info(f"✨ LLM enhanced search: {filters.search} → {len(all_terms)} terms")
            except Exception as semantic_error:
                logger.warning(f"Semantic search enhancement failed: {semantic_error}")

        # Build WHERE clause
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Validate and cap limit
        limit = min(filters.limit or 50, 500)  # Max 500 results

        # Build ORDER BY clause
        order_by_map = {
            "most_recent": "scraped_at DESC",
            "highest_salary": "salary_max DESC NULLS LAST, salary_min DESC NULLS LAST",
            "company_az": "company ASC",
            "h1b_rate": "h1b_approval_rate DESC NULLS LAST"
        }
        order_by = order_by_map.get(filters.sort_by, "scraped_at DESC")

        # Execute query
        query = f"""
            SELECT
                job_id,
                title,
                company,
                location,
                url,
                description,
                snippet,
                job_type,
                posted_date,
                salary_min,
                salary_max,
                salary_text,
                h1b_sponsor,
                h1b_approval_rate,
                h1b_total_petitions,
                h1b_employer_name,
                h1b_city,
                h1b_state,
                h1b_avg_wage,
                sponsorship_score,
                h1b_risk_level,
                work_model,
                visa_category,
                days_since_posted,
                classification_confidence,
                department,
                company_size,
                h1b_sponsored_explicit,
                is_new_grad_role,
                job_category,
                source,
                scraped_at
            FROM jobs_processed
            {where_sql}
            ORDER BY {order_by}
            LIMIT {limit}
        """

        logger.info(f"Executing jobs search query with limit={limit}: {query[:200]}...")
        cursor.execute(query)

        columns = [col[0].lower() for col in cursor.description]
        jobs = []

        for row in cursor.fetchall():
            job = {}
            for i, col in enumerate(columns):
                value = row[i]
                # Convert dates to strings
                if isinstance(value, (date, datetime)):
                    job[col] = value.isoformat()
                else:
                    job[col] = value
            jobs.append(job)

        logger.info(f"✅ Found {len(jobs)} jobs matching filters")

        return JobsResponse(
            jobs=jobs,
            total=len(jobs),
            filters_applied={
                "search": filters.search,
                "companies": filters.companies,
                "locations": filters.locations,
                "work_models": filters.work_models,
                "visa_sponsorship": filters.visa_sponsorship,
                "salary_range": f"${filters.salary_min or 0}-${filters.salary_max or 'max'}",
                "posted_within_days": filters.posted_within_days,
                "sort_by": filters.sort_by
            }
        )

    except Exception as e:
        logger.error(f"❌ Jobs search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/stats")
async def get_job_stats():
    """
    Get overall job statistics

    **Returns:**
    - total_jobs: Total number of jobs
    - unique_companies: Number of unique companies
    - h1b_sponsors: Companies offering H-1B sponsorship
    - remote_jobs: Number of remote positions
    - new_today: Jobs posted today
    - new_this_week: Jobs posted in last 7 days
    - avg_salary: Average minimum salary
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()

        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")

        # Get comprehensive stats
        cursor.execute("""
            SELECT
                COUNT(*) as total_jobs,
                COUNT(DISTINCT company) as unique_companies,
                COUNT(DISTINCT CASE WHEN h1b_sponsor = TRUE THEN company END) as h1b_sponsors,
                COUNT(CASE WHEN work_model = 'Remote' THEN 1 END) as remote_jobs,
                COUNT(CASE WHEN posted_date = CURRENT_DATE() THEN 1 END) as new_today,
                COUNT(CASE WHEN posted_date >= DATEADD(day, -7, CURRENT_DATE()) THEN 1 END) as new_this_week,
                AVG(CASE WHEN salary_min > 0 THEN salary_min END) as avg_salary
            FROM jobs_processed
        """)

        row = cursor.fetchone()

        return {
            "total_jobs": row[0] or 0,
            "unique_companies": row[1] or 0,
            "h1b_sponsors": row[2] or 0,
            "remote_jobs": row[3] or 0,
            "new_today": row[4] or 0,
            "new_this_week": row[5] or 0,
            "avg_salary": round(row[6], 2) if row[6] else None
        }

    except Exception as e:
        logger.error(f"❌ Job stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/companies")
async def get_companies():
    """Get list of all companies for filter dropdown with AI-powered data quality"""
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()

        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")

        # Get raw company data
        cursor.execute("""
            SELECT DISTINCT company, COUNT(*) as job_count
            FROM jobs_processed
            WHERE company IS NOT NULL
                AND company != ''
            GROUP BY company
            HAVING COUNT(*) >= 5
            ORDER BY job_count DESC
            LIMIT 150
        """)

        raw_companies = [{"name": row[0], "job_count": row[1]} for row in cursor.fetchall()]

        # Use LLM to filter out invalid companies and provide insights
        if len(raw_companies) > 0:
            companies_list = ", ".join([c["name"] for c in raw_companies[:50]])

            prompt = f"""Analyze this list of company names from a job database and identify which are INVALID/JUNK entries.

COMPANY LIST:
{companies_list}

INVALID ENTRIES (mark these for removal):
- US state names (California, Texas, New York, etc.)
- Generic terms (Enterprise, Corporation, Company, Inc, LLC, USA, United States)
- Single letters or abbreviations (A, B, C, AR, STR, NA)
- Location names (Remote, Hybrid, Boston, Seattle)
- Obvious data errors (numbers, symbols, corrupted text)

Respond with ONLY a JSON array of company names to KEEP (exclude invalid ones):
["Google", "Microsoft", "Amazon", ...]

Keep real company names even if they seem generic (e.g., "Accenture", "Deloitte" are valid)."""

            prompt_escaped = prompt.replace("'", "''")

            try:
                sql = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'mistral-large2',
                        '{prompt_escaped}'
                    )
                """
                cursor.execute(sql)
                response = cursor.fetchone()[0]

                # Parse LLM response
                json_match = re.search(r'\[.*?\]', response, re.DOTALL)
                if json_match:
                    valid_companies = json.loads(json_match.group(0))
                    # Filter companies based on LLM recommendations
                    filtered_companies = [
                        c for c in raw_companies
                        if c["name"] in valid_companies
                    ][:100]
                    logger.info(f"✨ LLM filtered {len(raw_companies)} → {len(filtered_companies)} companies")
                    return {"companies": filtered_companies}
            except Exception as llm_error:
                logger.warning(f"LLM filtering failed: {llm_error}, using fallback")

        # Fallback to manual filtering
        invalid_terms = ['United States', 'Enterprise', 'STR', 'AR', 'Remote', 'USA',
                        'Hybrid', 'Corporation', 'Company', 'Inc', 'LLC']
        companies = [
            c for c in raw_companies
            if c["name"] not in invalid_terms and len(c["name"]) > 2
        ][:100]

        return {"companies": companies}

    except Exception as e:
        logger.error(f"❌ Get companies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.get("/locations")
async def get_locations():
    """Get list of all locations for filter dropdown with AI-powered standardization"""
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()

        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")

        cursor.execute("""
            SELECT DISTINCT location, COUNT(*) as job_count
            FROM jobs_processed
            WHERE location IS NOT NULL
                AND location != ''
            GROUP BY location
            HAVING COUNT(*) >= 10
            ORDER BY job_count DESC
            LIMIT 80
        """)

        raw_locations = [{"name": row[0], "job_count": row[1]} for row in cursor.fetchall()]

        # Use LLM to clean and standardize location data
        if len(raw_locations) > 0:
            locations_list = ", ".join([loc["name"] for loc in raw_locations[:60]])

            prompt = f"""Analyze this list of job locations and provide cleaned/standardized versions.

RAW LOCATIONS:
{locations_list}

TASK:
1. Remove generic/invalid entries ("Remote", "USA", "Hybrid", "United States", "N/A")
2. Standardize city names ("SF" → "San Francisco", "NYC" → "New York")
3. Keep format: "City, State" or "City, Country" for international
4. Group similar locations ("San Francisco, CA" and "San Francisco" → "San Francisco, CA")

Respond with JSON object mapping standardized location to total count:
{{
  "San Francisco, CA": 150,
  "New York, NY": 120,
  "Seattle, WA": 100
}}

Only include real, specific locations (cities/states, not generic terms)."""

            prompt_escaped = prompt.replace("'", "''")

            try:
                sql = f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE(
                        'mistral-large2',
                        '{prompt_escaped}'
                    )
                """
                cursor.execute(sql)
                response = cursor.fetchone()[0]

                # Parse LLM response
                json_match = re.search(r'\{.*?\}', response, re.DOTALL)
                if json_match:
                    standardized_locs = json.loads(json_match.group(0))
                    locations = [
                        {"name": name, "job_count": count}
                        for name, count in sorted(standardized_locs.items(),
                                                 key=lambda x: x[1], reverse=True)
                    ][:50]
                    logger.info(f"✨ LLM standardized {len(raw_locations)} → {len(locations)} locations")
                    return {"locations": locations}
            except Exception as llm_error:
                logger.warning(f"LLM standardization failed: {llm_error}, using fallback")

        # Fallback to manual filtering
        invalid_terms = ['Remote', 'USA', 'Hybrid', 'United States', 'N/A', 'NA']
        locations = [
            loc for loc in raw_locations
            if loc["name"] not in invalid_terms and len(loc["name"]) > 2
        ][:50]

        return {"locations": locations}

    except Exception as e:
        logger.error(f"❌ Get locations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()
