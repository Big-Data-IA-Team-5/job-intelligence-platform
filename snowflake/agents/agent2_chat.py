"""
Agent 2: Job Intelligence Chat Agent (Production-Ready)
Uses pre-written SQL templates + Cortex for formatting answers
"""
import snowflake.connector
import os
from dotenv import load_dotenv
from typing import Dict, List
import json
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv('config/.env')


class JobIntelligenceAgent:
    """Production-ready chat agent with template-based queries."""
    
    def __init__(self):
        self.conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            database='job_intelligence',
            schema='processed',
            warehouse='compute_wh'
        )
        logger.info("✅ Agent 2 (Chat Intelligence) initialized")
    
    def _analyze_intent_with_llm(self, question: str, resume_context: str = None) -> Dict:
        """Use Snowflake Cortex LLM to analyze user intent and extract entities with full schema awareness and resume context."""
        cursor = self.conn.cursor()
        
        try:
            # Add resume context if available
            resume_section = ""
            if resume_context:
                resume_section = f"""

**USER'S RESUME CONTEXT:**
{resume_context[:1000]}

Based on the resume, extract relevant skills, experience, and preferences to personalize the job search."""

            prompt = f"""You are an intelligent career advisor and SQL expert analyzing job search questions. You have access to these database tables:

**DATABASE SCHEMA:**

1. **H1B_RAW** (479,005 rows, 97 columns) - H-1B visa sponsorship data:
   - employer_name, employer_poc_email, employer_poc_phone, employer_poc_job_title
   - job_title, worksite_city, worksite_state, worksite_postal_code
   - wage_rate_of_pay_from, wage_rate_of_pay_to, wage_unit_of_pay (Hour/Year), prevailing_wage
   - case_status (Certified/Denied), case_number, received_date, decision_date
   - visa_class, job_order_id, soc_code, soc_title
   - agent_attorney_first_name, agent_attorney_last_name, agent_attorney_email_address, agent_attorney_phone
   - lawfirm_name_business_name, naics_code, total_workers, new_employment
   - continued_employment, change_previous_employment, new_concurrent_employment

2. **JOBS_RAW** (16,358 rows, 21 columns) - Job postings:
   - id, title, company, location, description, requirements
   - url, date_posted, employment_type, salary_min, salary_max, currency
   - visa_category, h1b_sponsor, skills, experience_level, education_level
   - industry, benefits, application_deadline, scraped_date

**Your Task:**
Analyze this question and extract structured information: "{question}"

Return a JSON object with:
- intent: one of [job_search, salary_info, h1b_sponsorship, contact_info, company_comparison, resume_analysis, career_advice, general]
- job_title: normalized job role (e.g., "Software Engineer", "Data Analyst", "Data Intern") - if resume provided, infer from skills/experience
- location: city or state (e.g., "Boston", "Seattle", "MA", "WA") - if resume provided, check for location preferences
- company: company name if mentioned (single company) OR array of companies for comparison (e.g., ["Amazon", "Google"])
- keywords: important search terms from the question
- resume_skills: if resume provided, extract key technical skills (e.g., ["Python", "AWS", "Docker"])

**Examples:**
"looking for data related internship" → {{"intent": "job_search", "job_title": "Data Intern", "location": null, "company": null, "keywords": ["data", "internship"]}}
"what's the salary for SDE at Amazon in Seattle" → {{"intent": "salary_info", "job_title": "Software Engineer", "location": "Seattle", "company": "Amazon", "keywords": ["salary", "SDE"]}}
"find ML engineer jobs in Boston" → {{"intent": "job_search", "job_title": "Machine Learning Engineer", "location": "Boston", "company": null, "keywords": ["ML", "engineer"]}}
"which companies sponsor H-1B for data roles" → {{"intent": "h1b_sponsorship", "job_title": "Data", "location": null, "company": null, "keywords": ["sponsor", "H-1B", "data"]}}
"who should I contact at Google" → {{"intent": "contact_info", "job_title": null, "location": null, "company": "Google", "keywords": ["contact"]}}
"compare Amazon and Microsoft" → {{"intent": "company_comparison", "job_title": null, "location": null, "company": ["Amazon", "Microsoft"], "keywords": ["compare"]}}
"analyze my resume" → {{"intent": "resume_analysis", "job_title": null, "location": null, "company": null, "keywords": ["resume", "analyze"]}}
"what jobs match my resume" → {{"intent": "job_search", "job_title": "from_resume", "location": "from_resume", "company": null, "keywords": ["match", "resume"], "resume_skills": ["skill1", "skill2"]}}
"give me career advice" → {{"intent": "career_advice", "job_title": null, "location": null, "company": null, "keywords": ["career", "advice"]}}

**Question to analyze:** "{question}"
{resume_section}

Respond ONLY with the JSON object, no other text."""

            sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                '{prompt.replace("'", "''")}'
            ) as analysis
            """
            
            cursor.execute(sql)
            result = cursor.fetchone()
            
            if result and result[0]:
                # Parse LLM response
                response_text = result[0].strip()
                logger.info(f"🤖 LLM Response: {response_text[:500]}")
                
                # Extract JSON from response (LLM might add extra text)
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                    logger.info(f"✅ Parsed analysis: {analysis}")
                    return analysis
                else:
                    logger.warning(f"❌ No JSON found in LLM response")
            
            logger.warning("❌ No result from LLM, using fallback")
            return {"intent": "general", "job_title": None, "location": None, "company": None, "keywords": []}
            
        except Exception as e:
            logger.error(f"❌ LLM intent analysis failed: {e}, falling back to regex")
            import traceback
            traceback.print_exc()
            return {"intent": "general", "job_title": None, "location": None, "company": None, "keywords": []}
        finally:
            cursor.close()
    
    def ask(self, question: str, resume_context: str = None) -> Dict:
        """
        Answer questions using LLM-powered SQL generation with resume awareness.
        
        Supports ANY question about:
        - Job search, salary info, H-1B sponsorship, company comparisons, resume analysis, career advice
        """
        logger.info(f"❓ Question: {question}")
        if resume_context:
            logger.info(f"📄 Resume context provided ({len(resume_context)} chars)")
        
        # Use LLM to understand intent and extract entities (with resume context)
        intent_analysis = self._analyze_intent_with_llm(question, resume_context)
        
        logger.info(f"🧠 LLM Analysis: {intent_analysis}")
        
        # Extract entities (fallback to regex if LLM doesn't provide)
        company = intent_analysis.get('company') or self._extract_company(question)
        job_title = intent_analysis.get('job_title') or self._extract_job_title(question)
        location = intent_analysis.get('location') or self._extract_location(question)
        intent = intent_analysis.get('intent', 'general')
        
        logger.info(f"📊 Extracted - Intent: {intent}, Job: {job_title}, Location: {location}, Company: {company}")
        
        # Route based on LLM-detected intent
        if intent == 'resume_analysis':
            return self._analyze_resume(question, resume_context)
        
        elif intent == 'career_advice':
            return self._give_career_advice(question, resume_context, intent_analysis.get('resume_skills', []))
        
        elif intent == 'job_search':
            # If resume provided, use skills for better matching
            resume_skills = intent_analysis.get('resume_skills', [])
            return self._search_jobs(question, job_title, location, resume_skills, resume_context)
        
        elif intent == 'salary_info':
            return self._get_salary_info(job_title, location)
        
        elif intent == 'h1b_sponsorship':
            return self._get_sponsorship_info(company)
        
        elif intent == 'contact_info':
            return self._get_contact_info(company)
        
        elif intent == 'company_comparison':
            # Check if LLM extracted companies as array
            if isinstance(company, list):
                companies = company
            else:
                # Fallback to extraction
                companies = self._extract_multiple_companies(question)
                if not companies and company:
                    companies = [company]
            return self._compare_companies(companies)
        
        # Fallback to keyword matching if LLM intent is unclear
        else:
            q_lower = question.lower()
            
            if any(w in q_lower for w in ['looking for', 'find', 'search', 'jobs', 'openings', 'positions', 'show me', 'list', 'want job', 'need job', 'hiring', 'internship']):
                return self._search_jobs(question, job_title, location)
            
            elif any(w in q_lower for w in ['salary', 'pay', 'wage', 'how much', 'compensation', 'earn']):
                return self._get_salary_info(job_title, location)
            
            elif any(w in q_lower for w in ['sponsor', 'approval rate', 'h-1b', 'h1b', 'visa']):
                return self._get_sponsorship_info(company)
            
            elif any(w in q_lower for w in ['contact', 'email', 'attorney', 'lawyer', 'law firm', 'who should i']):
                return self._get_contact_info(company)
            
            elif any(w in q_lower for w in ['compare', 'vs', 'versus']):
                companies = self._extract_multiple_companies(question)
                return self._compare_companies(companies)
            
            else:
                return {
                    "answer": "I can help you with:\n- 🔍 **Job Search**: Find jobs, internships, openings\n- 💰 **Salary Info**: Average salaries, pay ranges\n- 🌐 **H-1B Sponsorship**: Companies, contacts, approval rates\n- 🏢 **Company Info**: Compare companies\n\nWhat would you like to know?",
                    "data": [],
                    "confidence": 0.5
                }
    
    def _get_contact_info(self, company: str) -> Dict:
        """Get employer + attorney contact information."""
        if not company:
            return self._error_response("Please specify a company name.")
        
        cursor = self.conn.cursor()
        
        try:
            # Get employer contact + attorney + law firm
            sql = f"""
            SELECT 
                employer_name,
                employer_poc_email,
                employer_poc_phone,
                employer_poc_job_title,
                agent_attorney_first_name,
                agent_attorney_last_name,
                agent_attorney_email_address,
                agent_attorney_phone,
                lawfirm_name_business_name,
                COUNT(*) OVER (PARTITION BY employer_name) as total_filings
            FROM raw.h1b_raw
            WHERE employer_name ILIKE '%{company}%'
              AND case_status = 'Certified'
              AND (employer_poc_email IS NOT NULL 
                   OR agent_attorney_email_address IS NOT NULL)
            ORDER BY received_date DESC
            LIMIT 5
            """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            if not results:
                # Try employer_intelligence
                sql2 = f"""
                SELECT 
                    employer_original,
                    sponsorship_score,
                    approval_rate,
                    total_filings
                FROM processed.employer_intelligence
                WHERE employer_clean ILIKE '%{company.upper()}%'
                LIMIT 1
                """
                cursor.execute(sql2)
                ei_results = cursor.fetchone()
                
                if ei_results:
                    return {
                        "answer": f"**{ei_results[0]}** sponsors H-1B visas:\n\n- Sponsorship Score: {ei_results[1]}/100\n- Approval Rate: {ei_results[2]*100:.0f}%\n- Total Filings: {ei_results[3]}\n\n⚠️ Contact information not available in public records. Reach out through company HR or careers page.",
                        "data": [{"employer": ei_results[0], "score": ei_results[1]}],
                        "confidence": 0.7
                    }
                else:
                    return self._error_response(f"No H-1B data found for {company}")
            
            # Format answer
            data = results[0]
            answer = f"**Contact Information for {data[0]}:**\n\n"
            
            if data[1]:  # POC email
                answer += f"📧 **Employer Immigration Contact:** {data[1]}\n"
            if data[2]:  # POC phone
                answer += f"📞 **Phone:** {data[2]}\n"
            if data[3]:  # POC title
                answer += f"👤 **Title:** {data[3]}\n"
            
            answer += "\n**Immigration Attorney Information:**\n"
            if data[4] and data[5]:  # Attorney name
                answer += f"👔 **Attorney:** {data[4]} {data[5]}\n"
            if data[6]:  # Attorney email
                answer += f"📧 **Email:** {data[6]}\n"
            if data[7]:  # Attorney phone
                answer += f"📞 **Phone:** {data[7]}\n"
            if data[8]:  # Law firm
                answer += f"🏢 **Law Firm:** {data[8]}\n"
            
            answer += f"\n📊 **H-1B Activity:** {data[9]} filings in database\n"
            
            answer += "\n**Next Steps:**\n"
            answer += f"1. Email {data[1] or data[6] or 'company HR'} to inquire about H-1B sponsorship\n"
            answer += "2. Mention you're on F-1 visa seeking sponsorship\n"
            answer += "3. Attach your resume and highlight relevant experience\n"
            
            return {
                "answer": answer,
                "data": [dict(zip(['employer', 'poc_email', 'attorney_email', 'law_firm'], 
                                 [data[0], data[1], data[6], data[8]]))],
                "sql_used": sql,
                "confidence": 0.95
            }
            
        except Exception as e:
            logger.error(f"Contact query error: {e}")
            return self._error_response(str(e))
        finally:
            cursor.close()
    
    def _get_salary_info(self, job_title: str, location: str) -> Dict:
        """Get salary statistics from H-1B data."""
        if not job_title:
            return self._error_response("Please specify a job title (e.g., Software Engineer, Data Analyst)")
        
        cursor = self.conn.cursor()
        
        try:
            sql = f"""
            SELECT 
                job_title,
                worksite_city,
                worksite_state,
                COUNT(*) as sample_size,
                ROUND(AVG(CASE 
                    WHEN wage_unit_of_pay = 'Hour' THEN wage_rate_of_pay_from * 2080
                    WHEN wage_unit_of_pay = 'Year' THEN wage_rate_of_pay_from
                    ELSE wage_rate_of_pay_from
                END), 0) as avg_salary,
                ROUND(MIN(wage_rate_of_pay_from), 0) as min_salary,
                ROUND(MAX(wage_rate_of_pay_from), 0) as max_salary,
                ROUND(AVG(prevailing_wage), 0) as prevailing_wage
            FROM raw.h1b_raw
            WHERE job_title ILIKE '%{job_title}%'
              {f"AND (worksite_city ILIKE '%{location}%' OR worksite_state ILIKE '%{location}%')" if location else ''}
              AND case_status = 'Certified'
              AND wage_rate_of_pay_from > 0
            GROUP BY job_title, worksite_city, worksite_state
            HAVING sample_size >= 5
            ORDER BY sample_size DESC
            LIMIT 10
            """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            if not results:
                return self._error_response(f"No salary data found for {job_title}" + (f" in {location}" if location else ""))
            
            # Format answer
            data = results[0]
            location_str = f"{data[1]}, {data[2]}" if data[1] else data[2] if data[2] else "United States"
            
            answer = f"**Salary Data for {data[0]}**"
            if location:
                answer += f" in {location_str}"
            answer += f" (based on {data[3]} H-1B cases):\n\n"
            
            answer += f"💰 **Average:** ${data[4]:,.0f}\n"
            answer += f"📊 **Range:** ${data[5]:,.0f} - ${data[6]:,.0f}\n"
            answer += f"📈 **Prevailing Wage:** ${data[7]:,.0f}\n"
            
            # Negotiation advice
            answer += "\n**💡 Negotiation Advice:**\n"
            if data[4] < data[7]:
                gap = data[7] - data[4]
                answer += f"- Target ${data[7]:,.0f} (prevailing wage)\n"
                answer += f"- Current average is ${gap:,.0f} below market\n"
            else:
                answer += f"- Competitive range: ${data[4]*0.9:,.0f} - ${data[4]*1.1:,.0f}\n"
            
            answer += f"- Don't accept below ${data[7]:,.0f} (prevailing wage floor)\n"
            
            # Show other locations if available
            if len(results) > 1:
                answer += f"\n**📍 Other Locations:**\n"
                for row in results[1:4]:
                    loc = f"{row[1]}, {row[2]}" if row[1] else row[2]
                    answer += f"- {loc}: ${row[4]:,.0f} avg ({row[3]} cases)\n"
            
            return {
                "answer": answer,
                "data": [{"job_title": data[0], "location": location_str, "avg_salary": data[4], "sample_size": data[3]}],
                "sql_used": sql,
                "confidence": 0.95
            }
            
        except Exception as e:
            logger.error(f"Salary query error: {e}")
            return self._error_response(str(e))
        finally:
            cursor.close()
    
    def _get_sponsorship_info(self, company: str) -> Dict:
        """Get H-1B sponsorship statistics."""
        if not company:
            return self._error_response("Please specify a company name.")
        
        cursor = self.conn.cursor()
        
        try:
            sql = f"""
            SELECT 
                employer_original,
                sponsorship_score,
                approval_rate,
                total_filings,
                total_certified,
                total_denied,
                filings_6mo,
                avg_wage_offered,
                is_violator,
                risk_level
            FROM processed.employer_intelligence
            WHERE employer_clean ILIKE '%{company.upper()}%'
               OR employer_original ILIKE '%{company}%'
            ORDER BY sponsorship_score DESC
            LIMIT 5
            """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            if not results:
                return self._error_response(f"No H-1B data found for {company}")
            
            data = results[0]
            answer = f"**{data[0]} H-1B Sponsorship Profile:**\n\n"
            
            # Sponsorship score
            score = data[1]
            if score >= 90:
                badge = "🟢 Excellent"
            elif score >= 70:
                badge = "🟡 Good"
            elif score >= 50:
                badge = "🟠 Fair"
            else:
                badge = "🔴 Risky"
            
            answer += f"**{badge} Sponsor** ({score:.1f}/100)\n\n"
            
            # Statistics
            answer += f"📊 **Statistics (FY2025 Q3):**\n"
            answer += f"- Approval Rate: {data[2]*100:.1f}%\n"
            answer += f"- Total Filings: {data[3]:,}\n"
            answer += f"- Certified: {data[4]:,}\n"
            answer += f"- Denied: {data[5]:,}\n"
            answer += f"- Recent Activity: {data[6]:,} filings in last 6 months\n"
            answer += f"- Average Salary Offered: ${data[7]:,.0f}\n"
            
            # Risk assessment
            answer += f"\n⚠️ **Risk Assessment:** {data[9]}\n"
            if data[8]:  # is_violator
                answer += "⛔ **WARNING:** Willful violator on record\n"
            
            # Recommendation
            answer += "\n**💡 Recommendation:**\n"
            if score >= 80:
                answer += "✅ Highly recommended - strong sponsorship history\n"
            elif score >= 60:
                answer += "✓ Good option - reliable sponsor\n"
            elif score >= 40:
                answer += "⚠️ Proceed with caution - limited history\n"
            else:
                answer += "🚫 Not recommended - high risk\n"
            
            return {
                "answer": answer,
                "data": [{"employer": data[0], "score": data[1], "approval_rate": data[2]}],
                "sql_used": sql,
                "confidence": 0.95
            }
            
        except Exception as e:
            logger.error(f"Sponsorship query error: {e}")
            return self._error_response(str(e))
        finally:
            cursor.close()
    
    def _compare_companies(self, companies: List[str]) -> Dict:
        """Compare multiple companies for H-1B sponsorship."""
        if len(companies) < 2:
            return self._error_response("Please specify at least 2 companies to compare.")
        
        cursor = self.conn.cursor()
        
        try:
            # Build ILIKE conditions
            conditions = " OR ".join([f"employer_clean ILIKE '%{c.upper()}%'" for c in companies[:3]])
            
            sql = f"""
            SELECT 
                employer_original,
                sponsorship_score,
                approval_rate,
                total_filings,
                avg_wage_offered,
                risk_level,
                filings_6mo
            FROM processed.employer_intelligence
            WHERE {conditions}
            ORDER BY sponsorship_score DESC
            """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            if not results:
                return self._error_response(f"No data found for companies: {', '.join(companies)}")
            
            # Format comparison
            answer = f"**H-1B Sponsorship Comparison:**\n\n"
            
            for i, data in enumerate(results, 1):
                answer += f"**{i}. {data[0]}**\n"
                answer += f"   • Score: {data[1]:.1f}/100\n"
                answer += f"   • Approval Rate: {data[2]*100:.1f}%\n"
                answer += f"   • Total Filings: {data[3]:,}\n"
                answer += f"   • Avg Salary: ${data[4]:,.0f}\n"
                answer += f"   • Risk: {data[5]}\n"
                answer += f"   • Recent: {data[6]:,} filings in 6mo\n\n"
            
            # Winner
            if len(results) >= 2:
                winner = results[0]
                answer += f"🏆 **Best Choice:** {winner[0]}\n"
                answer += f"   Higher score ({winner[1]:.1f} vs {results[1][1]:.1f}), "
                answer += f"better approval rate ({winner[2]*100:.0f}% vs {results[1][2]*100:.0f}%)\n"
            
            return {
                "answer": answer,
                "data": [{"employer": r[0], "score": r[1]} for r in results],
                "sql_used": sql,
                "confidence": 0.95
            }
            
        except Exception as e:
            logger.error(f"Comparison query error: {e}")
            return self._error_response(str(e))
        finally:
            cursor.close()
    
    def _search_jobs(self, question: str, job_title: str, location: str, resume_skills: List[str] = None, resume_context: str = None) -> Dict:
        """Search jobs using Agent 1."""
        try:
            import sys
            from pathlib import Path
            
            # Add parent directory to path
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))
            
            from snowflake.agents.agent1_search import JobSearchAgent
            
            # Enhance question with resume skills if provided
            enhanced_question = question
            if resume_skills:
                logger.info(f"🎯 Matching jobs with resume skills: {', '.join(resume_skills[:5])}")
                enhanced_question = f"{question} with skills: {', '.join(resume_skills[:5])}"
            
            agent1 = JobSearchAgent()
            result = agent1.search(enhanced_question)
            agent1.close()
            
            if result['status'] == 'success' and result['jobs']:
                # Return up to 10 jobs instead of 5
                jobs = result['jobs'][:10]
                total_available = result.get('total', len(jobs))
                
                answer = f"**Found {total_available} jobs** (showing {len(jobs)})\n\n"
                
                for i, job in enumerate(jobs, 1):
                    answer += f"**{i}. {job['TITLE']}**\n"
                    answer += f"   🏢 {job['COMPANY']} | 📍 {job['LOCATION']}\n"
                    answer += f"   🎫 {job['VISA_CATEGORY']}\n"
                    
                    if job.get('SALARY_MIN'):
                        answer += f"   💰 ${job['SALARY_MIN']:,} - ${job['SALARY_MAX']:,}\n"
                    
                    if job.get('SPONSORSHIP_SCORE'):
                        answer += f"   ⭐ Sponsor Score: {job['SPONSORSHIP_SCORE']:.0f}/100\n"
                    
                    answer += f"   🔗 {job['URL']}\n\n"
                
                return {
                    "answer": answer,
                    "data": jobs,
                    "sql_used": result.get('sql', ''),
                    "confidence": 0.9
                }
            else:
                return self._error_response("No jobs found. Try different search terms.")
                
        except Exception as e:
            logger.error(f"Job search error: {e}")
            return self._error_response(str(e))
    
    def _extract_company(self, text: str) -> str:
        """Extract company name."""
        companies = ['amazon', 'google', 'microsoft', 'meta', 'apple', 'snowflake',
                    'netflix', 'uber', 'airbnb', 'stripe', 'salesforce', 'oracle',
                    'ibm', 'intel', 'nvidia', 'adobe', 'cisco', 'dell', 'hp']
        
        t = text.lower()
        for comp in companies:
            if comp in t:
                return comp
        
        # Pattern: "at/for COMPANY"
        match = re.search(r'\b(?:at|for|with)\s+([A-Z][a-zA-Z\s&]+?)(?:\s|$|\?)', text)
        if match:
            return match.group(1).strip()
        
        return ''
    
    def _extract_job_title(self, text: str) -> str:
        """Extract job title."""
        titles = ['software engineer', 'data engineer', 'data analyst', 'data scientist',
                 'machine learning', 'product manager', 'devops', 'frontend', 'backend',
                 'full stack', 'cloud engineer', 'security engineer', 'data', 'sde',
                 'internship', 'intern', 'software developer', 'developer']
        
        t = text.lower()
        for title in titles:
            if title in t:
                # Return better formatted titles
                if title == 'data':
                    return 'data'
                elif title == 'sde':
                    return 'software engineer'
                elif title == 'internship' or title == 'intern':
                    return 'intern'
                return title
        return ''
    
    def _extract_location(self, text: str) -> str:
        """Extract location."""
        locations = ['boston', 'new york', 'nyc', 'san francisco', 'seattle', 'austin',
                    'chicago', 'denver', 'los angeles', 'la', 'bay area', 'remote']
        
        t = text.lower()
        for loc in locations:
            if loc in t:
                return loc
        return ''
    
    def _extract_multiple_companies(self, text: str) -> List[str]:
        """Extract multiple companies for comparison using pattern matching."""
        companies = []
        
        # Common patterns: "X and Y", "X vs Y", "X or Y", "X, Y", "compare X and Y"
        patterns = [
            r'\b([A-Z][a-zA-Z0-9\s&]+?)\s+(?:and|vs\.?|versus|or|,)\s+([A-Z][a-zA-Z0-9\s&]+?)\b',
            r'compare\s+([A-Z][a-zA-Z0-9\s&]+?)\s+(?:and|with|to)\s+([A-Z][a-zA-Z0-9\s&]+?)\b',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                comp1 = match.group(1).strip()
                comp2 = match.group(2).strip()
                # Clean up common words
                if comp1.lower() not in ['the', 'a', 'an', 'for', 'with', 'at']:
                    companies.append(comp1)
                if comp2.lower() not in ['the', 'a', 'an', 'for', 'with', 'at']:
                    companies.append(comp2)
        
        # Fallback: check hardcoded list for backward compatibility
        if not companies:
            common = ['amazon', 'google', 'microsoft', 'meta', 'apple', 'snowflake',
                     'dassault', 'boeing', 'lockheed', 'raytheon', 'northrop']
            t = text.lower()
            for comp in common:
                if comp in t:
                    companies.append(comp.title())
        
        return list(set(companies))  # Remove duplicates
    
    def _analyze_resume(self, question: str, resume_context: str = None) -> Dict:
        """Analyze resume and provide insights."""
        if not resume_context:
            return self._error_response("Please upload your resume first to get analysis.")
        
        try:
            # Use LLM to analyze resume
            prompt = f"""You are a professional career advisor. Analyze this resume and provide helpful insights.

Resume Content:
{resume_context[:2000]}

Provide:
1. **Strengths**: Key skills and experiences that stand out
2. **Improvement Areas**: What could be enhanced
3. **Recommended Roles**: Job titles that match this profile
4. **Next Steps**: Actionable career advice

Be specific and actionable."""

            sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                '{prompt.replace("'", "''")}'
            ) as analysis
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            
            analysis = result[0] if result else "Unable to analyze resume."
            
            return {
                "answer": analysis,
                "data": [],
                "confidence": 0.9
            }
            
        except Exception as e:
            logger.error(f"Resume analysis error: {e}")
            return self._error_response(str(e))
    
    def _give_career_advice(self, question: str, resume_context: str = None, resume_skills: List[str] = None) -> Dict:
        """Provide personalized career advice based on resume."""
        if not resume_context and not resume_skills:
            return self._error_response("Please upload your resume first to get personalized career advice.")
        
        try:
            skills_text = f"Skills: {', '.join(resume_skills[:10])}" if resume_skills else ""
            resume_text = resume_context[:1000] if resume_context else ""
            
            prompt = f"""You are an experienced career counselor specializing in tech careers. Provide personalized career advice.

User Question: {question}

{skills_text}

Resume Summary:
{resume_text}

Provide specific, actionable career advice addressing:
1. Career path recommendations based on current skills
2. Skills to develop for career growth
3. Industries/companies to target
4. Networking and job search strategies

Be encouraging and specific."""

            sql = f"""
            SELECT SNOWFLAKE.CORTEX.COMPLETE(
                'mistral-large2',
                '{prompt.replace("'", "''")}'
            ) as advice
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql)
            result = cursor.fetchone()
            cursor.close()
            
            advice = result[0] if result else "Unable to provide career advice."
            
            return {
                "answer": advice,
                "data": [],
                "confidence": 0.85
            }
            
        except Exception as e:
            logger.error(f"Career advice error: {e}")
            return self._error_response(str(e))
    
    def _error_response(self, message: str) -> Dict:
        """Standard error response."""
        return {
            "answer": f"❌ {message}",
            "data": [],
            "confidence": 0.0
        }
    
    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("🔌 Connection closed")