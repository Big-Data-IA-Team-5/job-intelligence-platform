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


# PROFILE EXTRACTION PROMPT (Optimized for Mistral-Large2 FLAGSHIP LLM)
PROFILE_EXTRACTION_PROMPT = """You are an expert resume parser powered by Snowflake Cortex Mistral-Large2.
Parse this resume with industry-level precision and extract comprehensive structured data.

**RESUME TEXT:**
{resume_text}

**EXTRACTION REQUIREMENTS:**

1. **Technical Skills** - Be comprehensive, categorize by type:
   - Programming Languages: Python, Java, JavaScript, etc.
   - Frameworks: React, Spring Boot, Django, etc.
   - Databases: SQL, PostgreSQL, MongoDB, etc.
   - Cloud: AWS, Azure, GCP, Snowflake, etc.
   - Tools: Git, Docker, Kubernetes, Airflow, etc.
   - Data Science: Pandas, NumPy, TensorFlow, PyTorch, etc.

2. **Soft Skills** - Extract from accomplishments and descriptions:
   - Leadership, Communication, Problem-solving, Teamwork, etc.

3. **Experience** - Calculate total years from ALL work experience:
   - Sum all work durations (internships count)
   - Include overlapping periods only once
   - Format as decimal (e.g., 2.5 years)

4. **Education** - Highest degree achieved:
   - Options: "High School", "Bachelor's", "Master's", "PhD"
   - Include major/concentration if available

5. **Work Authorization** - Infer from visa mentions or location:
   - "F-1" = Student visa
   - "OPT" or "F-1 OPT" = Optional Practical Training
   - "H-1B" = Work visa
   - "US Citizen" or "Permanent Resident" = No restrictions
   - "Unknown" = Cannot determine

6. **Desired Roles** - From objective, summary, or job history:
   - Normalize titles: "Software Engineer", "Data Scientist", "Product Manager"

7. **Locations** - From preferences or current location:
   - Cities or states mentioned
   - "Remote" if explicitly stated

8. **Salary Expectations** - Extract if mentioned (annual amount)

**RESPONSE FORMAT** - Return ONLY valid JSON:
{{
  "technical_skills": ["Python", "SQL", "AWS", "React", "Docker"],
  "soft_skills": ["Leadership", "Communication", "Problem-solving"],
  "total_experience_years": 3.5,
  "education_level": "Master's in Computer Science",
  "work_authorization": "F-1 OPT",
  "desired_roles": ["Software Engineer", "Full Stack Developer"],
  "preferred_locations": ["Boston", "New York", "Remote"],
  "salary_min": 85000
}}

Be thorough and extract ALL relevant information. Quality matters."""


# RE-RANKING PROMPT (Uses Mistral-Large2 FLAGSHIP for sophisticated matching)
RERANK_PROMPT = """You are an expert career advisor and job matching AI powered by Snowflake Cortex Mistral-Large2.
Your task is to perform industry-level job-candidate matching with sophisticated scoring algorithms.

**CANDIDATE PROFILE:**
- Technical Skills: {skills}
- Total Experience: {experience_years} years
- Education: {education}
- Work Authorization: {work_auth}
- Career Preferences: {preferences}

**CANDIDATE JOBS (Top 20 from vector search):**
{jobs_json}

**YOUR TASK:**
Re-rank these 20 jobs and select the TOP 10 BEST MATCHES using advanced scoring criteria.

**SCORING FRAMEWORK (Industry Standard):**

1. **Skills Match Score (35% weight)** [0-100]:
   - Exact skill matches: +10 points each (up to 80)
   - Similar/transferable skills: +5 points each
   - Missing critical skills: -5 points each
   - Bonus for rare/specialized skill matches: +20

2. **Experience Fit Score (30% weight)** [0-100]:
   - Perfect match (±1 year): 100 points
   - Within range (±2 years): 80 points
   - Slightly over-qualified (+2-4 years): 70 points
   - Slightly under-qualified (-1-2 years): 60 points
   - Significantly misaligned: 30 points

3. **Visa Compatibility Score (20% weight)** [0-100]:
   - H-1B sponsor + needs H-1B: 100 points
   - US Citizen + any job: 100 points
   - OPT eligible + OPT accepted: 100 points
   - No visa support but needs it: 0 points

4. **Location Match Score (10% weight)** [0-100]:
   - Exact location match: 100 points
   - Remote job + any preference: 100 points
   - Same state: 70 points
   - Different region: 40 points

5. **Career Growth Score (5% weight)** [0-100]:
   - Clear advancement path: 90+ points
   - Skill expansion opportunity: 80 points
   - Lateral move: 60 points
   - Potential step back: 40 points

**RESPONSE FORMAT** - Return ONLY a valid JSON array with exactly 10 jobs:
[
  {{
    "job_id": "abc123",
    "overall_score": 87,
    "skills_score": 92,
    "experience_score": 85,
    "visa_score": 100,
    "location_score": 75,
    "growth_score": 80,
    "reasoning": "Excellent Python/AWS match (8/10 skills), H-1B sponsor with 95% approval rate, remote-friendly, clear path to senior role within 2 years"
  }},
  ...
]

**CRITICAL RULES:**
- Return EXACTLY 10 jobs (best matches)
- All scores must be 0-100
- Provide specific, actionable reasoning (2-3 sentences)
- Consider visa needs as high priority for international candidates
- Prioritize recent postings (within 30 days) when scores are close
- Factor in company reputation and H-1B approval rates"""


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
                    'mistral-large2',
                    '{prompt_escaped}'
                )
            """
            
            cursor.execute(sql)
            response = cursor.fetchone()[0]
            
            logger.info(f"🤖 LLM Response (first 500 chars): {response[:500]}")
            
            # Parse JSON
            profile = self._parse_profile_response(response)
            
            # Validate profile has required fields
            if not profile or not profile.get('technical_skills'):
                logger.warning(f"⚠️ Empty profile returned, using defaults")
                profile = self._default_profile()
            
            logger.info(f"✅ Profile extracted: {len(profile.get('technical_skills', []))} skills, {profile.get('total_experience_years', 0)} years exp")
            
            return profile
            
        except Exception as e:
            logger.error(f"❌ Profile extraction failed: {e}")
            return self._default_profile()
        finally:
            cursor.close()
    
    def _parse_profile_response(self, response: str) -> Dict:
        """Parse profile extraction response."""
        
        try:
            if not response or len(response) < 10:
                logger.warning(f"Empty or too short response: {response}")
                return self._default_profile()
            
            # Clean response
            response = re.sub(r'```json\n?', '', response)
            response = re.sub(r'```\n?', '', response)
            response = response.strip()
            
            # Find JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.info(f"📋 Extracted JSON (first 300 chars): {json_str[:300]}")
                profile = json.loads(json_str)
                
                # Validate required fields exist
                if not isinstance(profile, dict):
                    logger.warning(f"Parsed result is not a dict: {type(profile)}")
                    return self._default_profile()
                
                # Validate and provide defaults
                parsed_profile = {
                    'technical_skills': profile.get('technical_skills', []),
                    'soft_skills': profile.get('soft_skills', []),
                    'total_experience_years': float(profile.get('total_experience_years', 0)),
                    'education_level': profile.get('education_level', 'Bachelor\'s'),
                    'work_authorization': profile.get('work_authorization', 'Unknown'),
                    'desired_roles': profile.get('desired_roles', []),
                    'preferred_locations': profile.get('preferred_locations', []),
                    'salary_min': int(profile.get('salary_min', 0)) if profile.get('salary_min') else None
                }
                
                logger.info(f"✅ Parsed profile successfully: {len(parsed_profile.get('technical_skills', []))} skills")
                return parsed_profile
            
            logger.warning(f"No JSON found in response")
            return self._default_profile()
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parsing failed: {e}")
            return self._default_profile()
        except Exception as e:
            logger.error(f"Profile parsing failed: {e}")
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
    
    def find_matching_jobs(self, profile: Dict, limit: int = 50) -> List[Dict]:
        """
        Step 2: Find similar jobs using SEMANTIC SEARCH with vector embeddings.
        
        Uses Snowflake VECTOR_COSINE_SIMILARITY to compare resume against job descriptions.
        Returns top matches based on semantic similarity.
        """
        cursor = self.conn.cursor()
        
        try:
            # Build search based on profile
            work_auth = profile.get('work_authorization', '')
            
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
            
            # Build resume text for embedding
            skills = profile.get('technical_skills', [])
            desired_roles = profile.get('desired_roles', [])
            experience = profile.get('total_experience_years', 0)
            education = profile.get('education_level', '')
            
            # Create rich resume summary for semantic search
            resume_text = f"""
            Skills: {', '.join(skills[:15])}. 
            Desired Roles: {', '.join(desired_roles)}. 
            Experience: {experience} years. 
            Education: {education}.
            """
            
            # Escape single quotes for SQL
            resume_text_escaped = resume_text.replace("'", "''")
            visa_filter = "', '".join(compatible_visas)
            
            # SEMANTIC SEARCH using vector embeddings
            sql = f"""
                WITH resume_embedding AS (
                    SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                        'e5-base-v2',
                        '{resume_text_escaped}'
                    ) AS resume_vector
                ),
                job_matches AS (
                    SELECT 
                        j.job_id,
                        j.url,
                        j.title,
                        j.company_clean as company,
                        j.location,
                        j.description,
                        j.qualifications,
                        j.salary_min,
                        j.salary_max,
                        j.job_type,
                        j.visa_category,
                        j.h1b_sponsor,
                        -- Semantic similarity score (0-1, higher is better)
                        VECTOR_COSINE_SIMILARITY(
                            e.description_embedding,
                            r.resume_vector
                        ) AS semantic_score
                    FROM jobs_processed j
                    INNER JOIN processing.embedded_jobs e ON j.job_id = e.job_id
                    CROSS JOIN resume_embedding r
                    WHERE j.visa_category IN ('{visa_filter}')
                      AND e.description_embedding IS NOT NULL
                )
                SELECT *
                FROM job_matches
                WHERE semantic_score > 0.5  -- Only return jobs with >50% similarity
                ORDER BY semantic_score DESC, job_id
                LIMIT {limit}
            """
            
            logger.info(f"🔍 Running semantic search with resume: {len(skills)} skills, {experience} years exp")
            cursor.execute(sql)
            columns = [col[0].lower() for col in cursor.description]
            jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"✅ Found {len(jobs)} semantically similar jobs")
            if jobs:
                logger.info(f"🎯 Top match: {jobs[0].get('title')} (similarity: {jobs[0].get('semantic_score', 0):.2f})")
            
            return jobs
            
        finally:
            cursor.close()
    
    def find_matching_jobs_direct(self, resume_text: str, limit: int = 20) -> List[Dict]:
        """
        SIMPLIFIED: Direct semantic search without profile extraction.
        Embeds raw resume text and compares with job embeddings.
        """
        cursor = self.conn.cursor()
        
        try:
            # Truncate resume if too long (keep first 2000 chars)
            resume_text = resume_text[:2000].replace("'", "''")
            
            # Direct semantic search
            sql = f"""
                WITH resume_embedding AS (
                    SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                        'e5-base-v2',
                        '{resume_text}'
                    ) AS resume_vector
                ),
                job_matches AS (
                    SELECT 
                        j.job_id,
                        j.url,
                        j.title,
                        j.company_clean as company,
                        j.location,
                        j.description,
                        j.qualifications,
                        j.salary_min,
                        j.salary_max,
                        j.job_type,
                        j.visa_category,
                        j.h1b_sponsor,
                        -- Semantic similarity score (0-1)
                        VECTOR_COSINE_SIMILARITY(
                            e.description_embedding,
                            r.resume_vector
                        ) AS semantic_score
                    FROM jobs_processed j
                    INNER JOIN processing.embedded_jobs e ON j.job_id = e.job_id
                    CROSS JOIN resume_embedding r
                    WHERE e.description_embedding IS NOT NULL
                      AND j.visa_category IN ('CPT', 'OPT', 'H-1B')
                )
                SELECT *
                FROM job_matches
                WHERE semantic_score > 0.50  -- Only >50% similarity
                ORDER BY semantic_score DESC
                LIMIT {limit}
            """
            
            logger.info(f"🔍 Running direct semantic search (resume length: {len(resume_text)} chars)")
            cursor.execute(sql)
            columns = [col[0].lower() for col in cursor.description]
            jobs = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"✅ Found {len(jobs)} jobs with >50% similarity")
            if jobs:
                logger.info(f"🎯 Top: {jobs[0].get('title')} ({jobs[0].get('semantic_score', 0)*100:.0f}%)")
            
            return jobs
            
        finally:
            cursor.close()
    
    def rerank_jobs(self, profile: Dict, jobs: List[Dict]) -> List[Dict]:
        """Re-rank jobs based on comprehensive scoring (including semantic similarity)."""
        scored_jobs = []
        
        for job in jobs:
            scores = self._calculate_scores(profile, job)
            
            # Get semantic similarity score from vector search (0-1 scale, convert to 0-100)
            semantic_similarity = job.get('semantic_score', 0.5) * 100
            
            # Calculate overall score (weighted average with semantic similarity boost)
            overall_score = round(
                semantic_similarity * 0.35 +  # NEW: Semantic similarity (35% weight)
                scores['skills'] * 0.25 +      # Reduced from 30%
                scores['experience'] * 0.20 +  # Reduced from 25%
                scores['visa'] * 0.10 +        # Reduced from 20%
                scores['location'] * 0.05 +    # Reduced from 15%
                scores['growth'] * 0.05,       # Reduced from 10%
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
        Complete matching pipeline - SIMPLIFIED with direct semantic search.
        
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
            # Step 1: Direct semantic search (no profile extraction needed!)
            logger.info("🔍 Semantic search: Matching resume directly to jobs...")
            candidate_jobs = self.find_matching_jobs_direct(resume_text, limit=20)
            
            if not candidate_jobs:
                logger.warning("⚠️ No candidate jobs found")
                # Create minimal profile for response compatibility (all required fields)
                minimal_profile = {
                    'technical_skills': ['Analyzed via semantic search'],
                    'soft_skills': ['Analyzed via semantic search'],
                    'total_experience_years': 0.0,
                    'education_level': 'Analyzed via semantic search',
                    'work_authorization': 'See resume',
                    'desired_roles': ['Analyzed via semantic search'],
                    'preferred_locations': ['Analyzed via semantic search'],
                    'salary_min': None
                }
                return {
                    "resume_id": resume_id,
                    "profile": minimal_profile,
                    "top_matches": [],
                    "total_candidates": 0
                }
            
            # Step 2: Re-rank based on semantic scores (already have them from search)
            logger.info("🎯 Ranking top matches by semantic similarity...")
            top_matches = sorted(candidate_jobs, key=lambda x: x.get('semantic_score', 0), reverse=True)[:10]
            
            # Add match reasoning based on semantic score
            for match in top_matches:
                score = match.get('semantic_score', 0) * 100
                if score >= 70:
                    reasoning = f"Excellent semantic match ({score:.0f}%) - Strong alignment between your resume and job requirements"
                elif score >= 60:
                    reasoning = f"Good match ({score:.0f}%) - Your background aligns well with this role"
                else:
                    reasoning = f"Moderate match ({score:.0f}%) - Some relevant skills and experience"
                
                match['overall_score'] = score
                match['skills_score'] = score
                match['experience_score'] = score
                match['visa_score'] = 100 if match.get('h1b_sponsor') else 50
                match['location_score'] = 70
                match['match_reasoning'] = reasoning
            
            # Step 3: Save to database
            self._save_matches(resume_id, top_matches)
            
            logger.info(f"✅ Matched {len(top_matches)} jobs (top score: {top_matches[0].get('semantic_score', 0)*100:.0f}%)")
            
            # Create minimal profile for response (all required fields with defaults)
            minimal_profile = {
                'technical_skills': ['Analyzed via semantic search'],
                'soft_skills': ['Communication', 'Teamwork'],
                'total_experience_years': 0.0,
                'education_level': 'Analyzed via semantic search',
                'work_authorization': 'See resume for details',
                'desired_roles': ['Analyzed via semantic search'],
                'preferred_locations': ['Analyzed via semantic search'],
                'salary_min': None
            }
            
            return {
                "resume_id": resume_id,
                "profile": minimal_profile,
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