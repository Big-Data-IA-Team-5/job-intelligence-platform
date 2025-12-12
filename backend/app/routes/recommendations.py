"""
Smart Job Recommendations API
Uses Snowflake Cortex LLM (mistral-large2) for intelligent job matching
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging
import re
import json

from app.utils.agent_wrapper import AgentManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class JobRecommendation(BaseModel):
    """Smart job recommendation with AI reasoning"""
    job_id: str
    title: str
    company: str
    location: str
    match_score: float
    reasons: List[str]
    url: Optional[str] = None


class RecommendationsResponse(BaseModel):
    """Job recommendations response"""
    recommendations: List[JobRecommendation]
    total: int
    analysis: str


@router.get("/smart-search", response_model=RecommendationsResponse)
async def smart_job_search(
    query: str = Query(..., description="Natural language job search query"),
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations")
):
    """
    Intelligent job search using LLM to understand intent and match jobs.

    **Examples:**
    - "entry level python jobs in San Francisco"
    - "remote senior software engineer with AWS experience"
    - "data scientist roles at startups with H-1B sponsorship"
    - "machine learning internships for students"

    **Returns:**
    - Ranked job recommendations with match scores
    - AI-generated reasons for each match
    - Overall search analysis
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()

        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")

        # Step 1: Use LLM to analyze search intent
        query_escaped = query.replace("'", "''")

        intent_prompt = f"""Analyze this job search query and extract structured search criteria:

QUERY: "{query}"

Extract:
1. Job titles/roles (be flexible with synonyms)
2. Required skills/technologies
3. Experience level (entry/mid/senior/intern)
4. Location preferences (city, state, remote)
5. Work model (remote/hybrid/onsite)
6. Visa requirements (H-1B/CPT/OPT)
7. Company preferences (if mentioned)
8. Special requirements

Respond with JSON:
{{
  "job_titles": ["Software Engineer", "Developer"],
  "skills": ["Python", "AWS"],
  "experience_level": "senior",
  "locations": ["San Francisco", "Remote"],
  "work_model": "remote",
  "visa_required": true,
  "company_size": "startup",
  "special_notes": "..."
}}

Be liberal with job title synonyms. For "software engineer" include "SWE", "Developer", "Programmer"."""

        prompt_escaped = intent_prompt.replace("'", "''")

        sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                '{prompt_escaped}'
            )
        """

        cursor.execute(sql)
        intent_response = cursor.fetchone()[0]

        # Parse LLM analysis
        json_match = re.search(r'\{.*?\}', intent_response, re.DOTALL)
        if not json_match:
            raise HTTPException(status_code=400, detail="Could not parse search query")

        intent_data = json.loads(json_match.group(0))

        logger.info(f"🧠 LLM parsed query: {intent_data}")

        # Step 2: Build SQL query based on intent
        where_clauses = []

        # Job titles (flexible matching)
        if intent_data.get('job_titles'):
            title_conditions = []
            for title in intent_data['job_titles']:
                title_clean = title.replace("'", "''")
                title_conditions.append(f"LOWER(title) LIKE LOWER('%{title_clean}%')")
            if title_conditions:
                where_clauses.append(f"({' OR '.join(title_conditions)})")

        # Skills
        if intent_data.get('skills'):
            skill_conditions = []
            for skill in intent_data['skills']:
                skill_clean = skill.replace("'", "''")
                skill_conditions.append(f"LOWER(description) LIKE LOWER('%{skill_clean}%')")
            if skill_conditions:
                where_clauses.append(f"({' OR '.join(skill_conditions)})")

        # Experience level
        experience_map = {
            'entry': ["entry", "junior", "new grad", "0-2 years"],
            'mid': ["mid", "intermediate", "2-5 years"],
            'senior': ["senior", "lead", "principal", "staff", "5+ years"],
            'intern': ["intern", "internship", "co-op", "student"]
        }

        exp_level = intent_data.get('experience_level', '').lower()
        if exp_level in experience_map:
            exp_conditions = []
            for term in experience_map[exp_level]:
                exp_conditions.append(f"LOWER(title) LIKE LOWER('%{term}%')")
            if exp_conditions:
                where_clauses.append(f"({' OR '.join(exp_conditions)})")

        # Location
        if intent_data.get('locations'):
            loc_conditions = []
            for loc in intent_data['locations']:
                if loc.lower() == 'remote':
                    loc_conditions.append("work_model = 'Remote'")
                else:
                    loc_clean = loc.replace("'", "''")
                    loc_conditions.append(f"LOWER(location) LIKE LOWER('%{loc_clean}%')")
            if loc_conditions:
                where_clauses.append(f"({' OR '.join(loc_conditions)})")

        # Work model
        if intent_data.get('work_model'):
            model = intent_data['work_model'].capitalize()
            where_clauses.append(f"work_model = '{model}'")

        # Visa sponsorship
        if intent_data.get('visa_required'):
            where_clauses.append("h1b_sponsor = TRUE")

        # Build final query
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query_sql = f"""
            SELECT
                job_id,
                title,
                company,
                location,
                url,
                description,
                snippet,
                work_model,
                h1b_sponsor,
                h1b_employer_name,
                h1b_city,
                h1b_state,
                h1b_approval_rate,
                h1b_total_petitions,
                h1b_avg_wage,
                sponsorship_score,
                h1b_risk_level,
                h1b_sponsored_explicit,
                salary_min,
                salary_max,
                posted_date,
                job_type,
                visa_category,
                source
            FROM jobs_processed
            {where_sql}
            ORDER BY posted_date DESC
            LIMIT {limit * 2}
        """

        logger.info(f"📊 Executing search: {query_sql[:200]}...")
        cursor.execute(query_sql)

        jobs = []
        columns = [col[0].lower() for col in cursor.description]
        for row in cursor.fetchall():
            job = dict(zip(columns, row))
            jobs.append(job)

        if len(jobs) == 0:
            return RecommendationsResponse(
                recommendations=[],
                total=0,
                analysis=f"No jobs found matching '{query}'. Try broadening your search criteria."
            )

        # Step 3: Use LLM to rank and explain matches
        jobs_summary = "\n".join([
            f"{i+1}. {job['title']} at {job['company']} - {job['location']}"
            for i, job in enumerate(jobs[:20])
        ])

        ranking_prompt = f"""You are a job matching expert. Rank these jobs for this query: "{query}"

JOBS FOUND:
{jobs_summary}

ORIGINAL QUERY INTENT:
{json.dumps(intent_data, indent=2)}

For each job (by number), provide:
1. Match score (0-100) based on how well it matches the query
2. Top 3 reasons why it's a good match

Respond with JSON array:
[
  {{
    "job_number": 1,
    "match_score": 95,
    "reasons": ["Perfect title match", "Location match", "H-1B sponsor"]
  }},
  ...
]

Only include jobs with score >= 60. Sort by match_score descending."""

        ranking_escaped = ranking_prompt.replace("'", "''")

        ranking_sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                '{ranking_escaped}'
            )
        """

        cursor.execute(ranking_sql)
        ranking_response = cursor.fetchone()[0]

        # Parse rankings
        json_match = re.search(r'\[.*?\]', ranking_response, re.DOTALL)
        if json_match:
            rankings = json.loads(json_match.group(0))

            # Build recommendations
            recommendations = []
            for rank in rankings[:limit]:
                job_idx = rank['job_number'] - 1
                if 0 <= job_idx < len(jobs):
                    job = jobs[job_idx]
                    recommendations.append(JobRecommendation(
                        job_id=job['job_id'],
                        title=job['title'],
                        company=job['company'],
                        location=job['location'],
                        match_score=rank['match_score'],
                        reasons=rank.get('reasons', []),
                        url=job.get('url')
                    ))

            analysis = f"Found {len(jobs)} jobs matching your query. Showing top {len(recommendations)} recommendations based on AI analysis."

            logger.info(f"✨ Smart search completed: {len(recommendations)} recommendations")

            return RecommendationsResponse(
                recommendations=recommendations,
                total=len(jobs),
                analysis=analysis
            )

        # Fallback: Return top jobs without ranking
        recommendations = [
            JobRecommendation(
                job_id=job['job_id'],
                title=job['title'],
                company=job['company'],
                location=job['location'],
                match_score=80.0,
                reasons=["Matches search criteria"],
                url=job.get('url')
            )
            for job in jobs[:limit]
        ]

        return RecommendationsResponse(
            recommendations=recommendations,
            total=len(jobs),
            analysis=f"Found {len(jobs)} jobs. Showing top {len(recommendations)}."
        )

    except json.JSONDecodeError as je:
        logger.error(f"JSON parse error: {je}")
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        logger.error(f"Smart search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()


@router.post("/similar-jobs/{job_id}")
async def find_similar_jobs(
    job_id: str,
    limit: int = Query(10, ge=1, le=20)
):
    """
    Find jobs similar to a given job using LLM analysis.

    **Returns:**
    - Similar jobs ranked by relevance
    - AI explanation of similarity
    """
    agent = None
    try:
        agent = AgentManager.get_search_agent()
        cursor = agent.conn.cursor()

        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA processed")

        # Get source job
        job_id_clean = job_id.replace("'", "''")
        cursor.execute(f"""
            SELECT title, company, location, description, snippet
            FROM jobs_processed
            WHERE job_id = '{job_id_clean}'
        """)

        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Job not found")

        source_job = {
            'title': result[0],
            'company': result[1],
            'location': result[2],
            'description': result[3],
            'snippet': result[4]
        }

        # Use LLM to analyze job and find similar characteristics
        analysis_prompt = f"""Analyze this job and identify key characteristics to find similar jobs:

JOB:
Title: {source_job['title']}
Company: {source_job['company']}
Location: {source_job['location']}
Description: {source_job['snippet'][:500]}

Identify:
1. Job role/function (e.g., "Backend Engineer", "Data Analyst")
2. Key skills/technologies required
3. Experience level
4. Industry/domain

Respond with JSON:
{{
  "role": "...",
  "skills": ["...", "..."],
  "level": "...",
  "industry": "..."
}}"""

        prompt_escaped = analysis_prompt.replace("'", "''")

        sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                '{prompt_escaped}'
            )
        """

        cursor.execute(sql)
        analysis_response = cursor.fetchone()[0]

        # Parse and search for similar jobs
        json_match = re.search(r'\{.*?\}', analysis_response, re.DOTALL)
        if json_match:
            characteristics = json.loads(json_match.group(0))

            # Build search for similar jobs
            search_conditions = []
            if characteristics.get('role'):
                role = characteristics['role'].replace("'", "''")
                search_conditions.append(f"LOWER(title) LIKE LOWER('%{role}%')")

            if characteristics.get('skills'):
                for skill in characteristics['skills'][:3]:
                    skill_clean = skill.replace("'", "''")
                    search_conditions.append(f"LOWER(description) LIKE LOWER('%{skill_clean}%')")

            where_sql = "WHERE " + " OR ".join(search_conditions) if search_conditions else ""

            cursor.execute(f"""
                SELECT job_id, title, company, location, url, snippet,
                       h1b_sponsor, h1b_approval_rate, h1b_total_petitions,
                       salary_min, salary_max, work_model, posted_date
                FROM jobs_processed
                {where_sql}
                AND job_id != '{job_id_clean}'
                ORDER BY posted_date DESC
                LIMIT {limit}
            """)

            similar_jobs = [
                {
                    'job_id': row[0],
                    'title': row[1],
                    'company': row[2],
                    'location': row[3],
                    'url': row[4],
                    'snippet': row[5],
                    'h1b_sponsor': row[6],
                    'h1b_approval_rate': row[7],
                    'h1b_total_petitions': row[8],
                    'salary_min': row[9],
                    'salary_max': row[10],
                    'work_model': row[11],
                    'posted_date': row[12]
                }
                for row in cursor.fetchall()
            ]

            return {
                'source_job': source_job,
                'similar_jobs': similar_jobs,
                'analysis': f"Found {len(similar_jobs)} similar jobs based on role: {characteristics.get('role', 'similar position')}"
            }

        raise HTTPException(status_code=500, detail="Could not analyze job")

    except Exception as e:
        logger.error(f"Similar jobs error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if agent:
            agent.close()
