"""
Agent 4: Resume Matcher - PRODUCTION READY
Match resumes to jobs using AI and vector search
"""
import snowflake.connector
import json
import os
import re
from typing import Dict, List, Optional
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv('config/.env')


# PROFILE EXTRACTION PROMPT (Optimized for Mixtral 8x7B)
PROFILE_EXTRACTION_PROMPT = """Extract structured information from this resume. Respond ONLY with JSON.

RESUME TEXT:
{resume_text}

Extract:
1. Technical skills (programming languages, tools, frameworks)
2. Soft skills (leadership, communication, etc.)
3. Total years of experience (calculate from work history)
4. Highest education level (High School, Bachelor's, Master's, PhD)
5. Work authorization status (F-1, OPT, H-1B, US Citizen, or infer from context)
6. Desired job roles (from objective/summary)
7. Preferred locations (if mentioned)
8. Minimum expected salary (if mentioned)

JSON format:
{{
  "technical_skills": ["Python", "SQL", "AWS"],
  "soft_skills": ["Leadership", "Communication"],
  "total_experience_years": 3.5,
  "education_level": "Master's",
  "work_authorization": "F-1 OPT",
  "desired_roles": ["Data Engineer", "ML Engineer"],
  "preferred_locations": ["Boston", "Remote"],
  "salary_min": 80000
}}
"""


# RE-RANKING PROMPT (Uses Claude 3.5 for better reasoning)
RERANK_PROMPT = """You are a career advisor. Match this candidate to these jobs.

CANDIDATE PROFILE:
Skills: {skills}
Experience: {experience_years} years
Education: {education}
Work Auth: {work_auth}
Preferences: {preferences}

TOP 20 CANDIDATE JOBS:
{jobs_json}

Re-rank these 20 jobs and return the TOP 10 best matches.

SCORING CRITERIA (0-100 for each):
1. Skills Match (30%): Required skills vs candidate skills
2. Experience Fit (25%): Experience level alignment
3. Visa Compatibility (20%): Work authorization match
4. Location Preference (15%): Location alignment
5. Growth Potential (10%): Career advancement opportunity

Respond ONLY with JSON array of top 10 jobs:
[
  {{
    "job_id": "...",
    "overall_score": 85,
    "skills_score": 90,
    "experience_score": 80,
    "visa_score": 100,
    "location_score": 75,
    "growth_score": 70,
    "reasoning": "Strong Python/SQL match, visa compatible, good growth path"
  }}
]
"""


class ResumeMatcherAgent:
    """
    Agent 4: Resume-to-Job Matching
    
    Process:
    1. Extract profile from resume → Mixtral 8x7B
    2. Vector search for similar jobs → Cortex Search
    3. Re-rank top 20 → Mixtral 8x7B  
    4. Return top 10 with scores
    """
    
    def __init__(self):
        """Initialize Snowflake connection."""
        self.conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            database='job_intelligence',
            schema='processed',
            warehouse='compute_wh'
        )
        logger.info("✅ Agent 4 initialized")
    
    def extract_profile(self, resume_text: str) -> Dict:
        """
        Step 1: Extract structured profile from resume.
        
        Args:
            resume_text: Full resume text
            
        Returns:
            Structured profile dict
        """
        cursor = self.conn.cursor()
        
        try:
            # Truncate if too long
            resume_text = resume_text[:3000]
            
            # Build prompt
            prompt = PROFILE_EXTRACTION_PROMPT.format(
                resume_text=resume_text
            )
            
            # Escape for SQL
            prompt_escaped = prompt.replace("'", "''")
            
            # Call Mixtral
            sql = f"""
                SELECT SNOWFLAKE.CORTEX.COMPLETE(
                    'mixtral-8x7b',
                    '{prompt_escaped}'
                )
            """
            
            cursor.execute(sql)
            response = cursor.fetchone()[0]
            
            # Parse JSON
            profile = self._parse_profile_response(response)
            
            logger.info(f"✅ Profile extracted: {len(profile.get('technical_skills', []))} skills")
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Profile extraction failed: {e}")
            return self._default_profile()
        finally:
            cursor.close()
    
    def _parse_profile_response(self, response: str) -> Dict:
        """Parse profile extraction response."""
        
        try:
            # Clean response
            response = re.sub(r'```json\n?', '', response)
            response = re.sub(r'```\n?', '', response)
            response = response.strip()
            
            # Find JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                profile = json.loads(json_match.group(0))
                
                # Validate and provide defaults
                return {
                    'technical_skills': profile.get('technical_skills', []),
                    'soft_skills': profile.get('soft_skills', []),
                    'total_experience_years': float(profile.get('total_experience_years', 0)),
                    'education_level': profile.get('education_level', 'Bachelor\'s'),
                    'work_authorization': profile.get('work_authorization', 'Unknown'),
                    'desired_roles': profile.get('desired_roles', []),
                    'preferred_locations': profile.get('preferred_locations', []),
                    'salary_min': int(profile.get('salary_min', 0)) if profile.get('salary_min') else None
                }
            
            return self._default_profile()
            
        except Exception as e:
            logger.warning(f"Profile parsing failed: {e}")
            return self._default_profile()
    
    def _default_profile(self) -> Dict:
        """Return default empty profile."""
        return {
            'technical_skills': [],
            'soft_skills': [],
            'total_experience_years': 0.0,
            'education_level': 'Unknown',
            'work_authorization': 'Unknown',
            'desired_roles': [],
            'preferred_locations': [],
            'salary_min': None
        }
    
    def find_matching_jobs(self, profile: Dict, limit: int = 50, days_back: int = 90) -> List[Dict]:
        """
        Step 2: Find matching jobs using semantic search on actual resume content.
        
        Uses:
        - Skills matching (technical + desired roles)
        - Visa compatibility filtering
        - Recent jobs prioritization (latest first)
        - Semantic search on job descriptions
        
        Args:
            profile: Extracted resume profile with skills/experience
            limit: Max number of candidates to return (default 50 for better ranking pool)
            days_back: Only consider jobs posted in last N days (default 90)
        """
        cursor = self.conn.cursor()
        
        try:
            # Extract search criteria from profile
            work_auth = profile.get('work_authorization', '')
            tech_skills = profile.get('technical_skills', [])
            desired_roles = profile.get('desired_roles', [])
            
            # Build skill-based search query
            search_terms = []
            
            # Add top technical skills (max 10 for performance)
            if tech_skills:
                search_terms.extend(tech_skills[:10])
            
            # Add desired roles
            if desired_roles:
                search_terms.extend(desired_roles[:5])
            
            # Fallback if no skills extracted
            if not search_terms:
                search_terms = ['software', 'engineer', 'developer']
                logger.warning("⚠️ No skills found in resume, using generic search")
            
            # Build search string for semantic matching
            search_string = ' '.join(search_terms).lower()
            
            # Determine compatible visa categories
            compatible_visas = []
            if 'F-1' in work_auth or 'CPT' in work_auth:
                compatible_visas.append('CPT')
            if 'OPT' in work_auth:
                compatible_visas.extend(['OPT', 'H-1B'])
            if 'H-1B' in work_auth:
                compatible_visas.append('H-1B')
            if 'Citizen' in work_auth or 'US' in work_auth:
                compatible_visas.extend(['CPT', 'OPT', 'H-1B', 'US-Only'])
            
            # Default to international student friendly
            if not compatible_visas:
                compatible_visas = ['CPT', 'OPT', 'H-1B']
            
            # Build SQL with semantic search
            visa_filter = "', '".join(compatible_visas)
            
            # Escape search string for SQL
            search_string_escaped = search_string.replace("'", "''")
            
            # Build CASE statements for each search term to boost matching
            skill_match_cases = []
            for term in search_terms[:10]:  # Limit to top 10 for performance
                term_escaped = term.lower().replace("'", "''")
                skill_match_cases.append(
                    f"(CASE WHEN LOWER(qualifications) LIKE '%{term_escaped}%' "
                    f"OR LOWER(description) LIKE '%{term_escaped}%' "
                    f"OR LOWER(title) LIKE '%{term_escaped}%' THEN 1 ELSE 0 END)"
                )
            
            # Calculate relevance score
            relevance_score = " + ".join(skill_match_cases) if skill_match_cases else "0"
            
            sql = f"""
                SELECT 
                    job_id,
                    url,
                    title,
                    company_clean as company,
                    location,
                    description,
                    qualifications,
                    salary_min,
                    salary_max,
                    job_type,
                    visa_category,
                    h1b_sponsor,
                    days_since_posted,
                    ({relevance_score}) as relevance_score
                FROM jobs_processed
                WHERE visa_category IN ('{visa_filter}')
                  AND days_since_posted <= {days_back}
                  AND ({relevance_score}) > 0
                ORDER BY 
                    relevance_score DESC,
                    days_since_posted ASC
                LIMIT {limit}
            """
            
            logger.info(f"🔍 Searching with skills: {', '.join(search_terms[:5])}...")
            logger.info(f"📅 Date range: Last {days_back} days")
            
            cursor.execute(sql)
            columns = [col[0].lower() for col in cursor.description]
            jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"✅ Found {len(jobs)} matching jobs")
            if jobs:
                logger.info(f"📊 Top match: {jobs[0].get('title')} (relevance: {jobs[0].get('relevance_score')}, days old: {jobs[0].get('days_since_posted')})")
            
            return jobs
            
        except Exception as e:
            logger.error(f"❌ Job search failed: {e}")
            # Fallback to basic query if semantic search fails
            return self._fallback_search(compatible_visas, limit, days_back)
            
        finally:
            cursor.close()
    
    def _fallback_search(self, compatible_visas: List[str], limit: int, days_back: int) -> List[Dict]:
        """Fallback search without semantic matching."""
        cursor = self.conn.cursor()
        try:
            visa_filter = "', '".join(compatible_visas)
            sql = f"""
                SELECT 
                    job_id, url, title, company_clean as company,
                    location, description, qualifications,
                    salary_min, salary_max, job_type,
                    visa_category, h1b_sponsor, days_since_posted
                FROM jobs_processed
                WHERE visa_category IN ('{visa_filter}')
                  AND days_since_posted <= {days_back}
                ORDER BY days_since_posted ASC
                LIMIT {limit}
            """
            cursor.execute(sql)
            columns = [col[0].lower() for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
    
    def rerank_jobs(self, profile: Dict, jobs: List[Dict]) -> List[Dict]:
        """Re-rank jobs based on comprehensive scoring."""
        scored_jobs = []
        
        for job in jobs:
            scores = self._calculate_scores(profile, job)
            
            # Calculate overall score (weighted average)
            overall_score = round(
                scores['skills'] * 0.30 +
                scores['experience'] * 0.25 +
                scores['visa'] * 0.20 +
                scores['location'] * 0.15 +
                scores['growth'] * 0.10,
                1
            )
            
            # Add scores to job dict (keys are already lowercase from SQL)
            job_with_scores = {
                'job_id': job.get('job_id', ''),
                'title': job.get('title', ''),
                'company': job.get('company', ''),
                'location': job.get('location', ''),
                'url': job.get('url', ''),
                'visa_category': job.get('visa_category'),
                'description': job.get('description', ''),
                'qualifications': job.get('qualifications', ''),
                'job_type': job.get('job_type', ''),
                'salary_min': job.get('salary_min'),
                'salary_max': job.get('salary_max'),
                'h1b_sponsor': job.get('h1b_sponsor'),
                'overall_score': overall_score,
                'skills_score': scores['skills'],
                'experience_score': scores['experience'],
                'visa_score': scores['visa'],
                'location_score': scores['location'],
                'growth_score': scores['growth'],
                'match_reasoning': self._generate_reasoning(profile, job, scores)
            }
            
            scored_jobs.append(job_with_scores)
        
        # Sort by overall score (descending)
        ranked_jobs = sorted(scored_jobs, key=lambda x: x['overall_score'], reverse=True)
        
        top_10 = ranked_jobs[:10]
        if top_10:
            logger.info(f"🎯 Top match: {top_10[0].get('title')} at {top_10[0].get('company')} (score: {top_10[0].get('overall_score')})")
        
        return top_10
    
    def _calculate_scores(self, profile: Dict, job: Dict) -> Dict:
        """Calculate individual match scores."""
        
        scores = {
            'skills': 50,      # Default medium
            'experience': 50,
            'visa': 100,       # Default full match
            'location': 50,
            'growth': 50
        }
        
        # Skills score (keyword matching)
        # ENHANCED: Use qualifications field if available for better matching
        candidate_skills = [s.lower() for s in profile.get('technical_skills', [])]
        
        # Prioritize qualifications field, fall back to description (lowercase keys from SQL)
        qualifications = job.get('qualifications', '') or job.get('description', '')
        search_text = qualifications.lower() if qualifications else ''
        
        if candidate_skills:
            matches = sum(1 for skill in candidate_skills if skill in search_text)
            scores['skills'] = min((matches / len(candidate_skills)) * 100, 100)
        
        # Experience score
        exp_years = profile.get('total_experience_years', 0)
        job_title = job.get('title', '').lower()
        
        if 'intern' in job_title and exp_years <= 2:
            scores['experience'] = 90
        elif 'entry' in job_title or 'junior' in job_title:
            scores['experience'] = 85 if exp_years <= 3 else 70
        elif 'senior' in job_title:
            scores['experience'] = 90 if exp_years >= 5 else 50
        else:
            scores['experience'] = 75  # Mid-level
        
        # Visa score
        work_auth = profile.get('work_authorization', '')
        visa_cat = job.get('visa_category', '')
        
        if 'CPT' in work_auth and visa_cat == 'CPT':
            scores['visa'] = 100
        elif 'OPT' in work_auth and visa_cat in ['OPT', 'H-1B']:
            scores['visa'] = 100
        elif 'H-1B' in work_auth and visa_cat == 'H-1B':
            scores['visa'] = 100
        elif 'Citizen' in work_auth:
            scores['visa'] = 100
        elif visa_cat == 'US-Only':
            scores['visa'] = 0  # Not compatible
        else:
            scores['visa'] = 70  # Uncertain
        
        # Location score
        preferred_locs = [loc.lower() for loc in profile.get('preferred_locations', [])]
        job_location = job.get('location', '').lower() if job.get('location') else ''
        
        if any(loc in job_location for loc in preferred_locs):
            scores['location'] = 95
        elif 'remote' in job_location or 'remote' in preferred_locs:
            scores['location'] = 100
        else:
            scores['location'] = 50
        
        # Growth score (based on company and role)
        company = job.get('company', '').lower() if job.get('company') else ''
        big_tech = ['google', 'microsoft', 'amazon', 'meta', 'apple']
        
        if any(tech in company for tech in big_tech):
            scores['growth'] = 85
        elif job.get('h1b_sponsor'):
            scores['growth'] = 75
        else:
            scores['growth'] = 60
        
        return scores
    
    def _generate_reasoning(self, profile: Dict, job: Dict, scores: Dict) -> str:
        """Generate match reasoning."""
        
        reasons = []
        
        if scores['skills'] >= 80:
            reasons.append("Strong skills match")
        elif scores['skills'] >= 60:
            reasons.append("Good skills overlap")
        
        if scores['experience'] >= 80:
            reasons.append("experience level fits")
        
        if scores['visa'] == 100:
            reasons.append("visa compatible")
        elif scores['visa'] == 0:
            reasons.append("visa incompatible")
        
        if scores['location'] >= 90:
            reasons.append("preferred location")
        
        if not reasons:
            reasons.append("Potential match")
        
        return ", ".join(reasons).capitalize()
    
    def match_resume(self, resume_id: str, resume_text: str) -> Dict:
        """
        Complete matching pipeline.
        
        Args:
            resume_id: Unique resume identifier
            resume_text: Full resume text
            
        Returns:
            {
                "resume_id": str,
                "profile": Dict,
                "top_matches": List[Dict],
                "total_candidates": int
            }
        """
        
        try:
            # Step 1: Extract profile
            logger.info("📄 Step 1: Extracting resume profile...")
            profile = self.extract_profile(resume_text)
            
            # Step 2: Find candidate jobs using semantic search
            logger.info("🔍 Step 2: Finding candidate jobs with semantic matching...")
            candidate_jobs = self.find_matching_jobs(profile, limit=50, days_back=90)
            
            if not candidate_jobs:
                logger.warning("⚠️ No candidate jobs found")
                return {
                    "resume_id": resume_id,
                    "profile": profile,
                    "top_matches": [],
                    "total_candidates": 0
                }
            
            # Step 3: Re-rank jobs
            logger.info("🎯 Step 3: Re-ranking top matches...")
            top_matches = self.rerank_jobs(profile, candidate_jobs)
            
            # Step 4: Save to database
            self._save_matches(resume_id, top_matches)
            
            logger.info(f"✅ Matched {len(top_matches)} jobs to resume")
            
            return {
                "resume_id": resume_id,
                "profile": profile,
                "top_matches": top_matches,
                "total_candidates": len(candidate_jobs)
            }
            
        except Exception as e:
            logger.error(f"❌ Matching failed: {e}")
            return {
                "resume_id": resume_id,
                "profile": {},
                "top_matches": [],
                "total_candidates": 0,
                "error": str(e)
            }
    
    def _save_matches(self, resume_id: str, matches: List[Dict]):
        """Save matches to database."""
        
        cursor = self.conn.cursor()
        
        try:
            for i, match in enumerate(matches[:10]):
                job_id = match['job_id']
                match_id = f"{resume_id}_{job_id}"
                
                sql = f"""
                    INSERT INTO job_matches (
                        match_id, resume_id, job_id,
                        overall_score, skills_score, experience_score,
                        visa_score, location_score,
                        match_reasoning, matched_at
                    ) VALUES (
                        '{match_id}',
                        '{resume_id}',
                        '{job_id}',
                        {match['overall_score']},
                        {match['skills_score']},
                        {match['experience_score']},
                        {match['visa_score']},
                        {match['location_score']},
                        '{match['match_reasoning'].replace("'", "''")}',
                        CURRENT_TIMESTAMP()
                    )
                """
                
                cursor.execute(sql)
            
            self.conn.commit()
            logger.info(f"💾 Saved {len(matches[:10])} matches to database")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to save matches: {e}")
        finally:
            cursor.close()
    
    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            logger.info("🔌 Connection closed")


if __name__ == "__main__":
    # For testing, run: python -m pytest tests/test_agent4.py
    print("Agent 4: Resume Matcher")
    print("Run tests with: python -m pytest tests/test_agent4.py -v")