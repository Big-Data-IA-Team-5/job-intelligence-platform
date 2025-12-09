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
    
    def _analyze_intent_with_llm(self, question: str, resume_context: str = None, chat_history: list = None) -> Dict:
        """Use Snowflake Cortex LLM to analyze user intent and extract entities with full schema awareness, resume context, and conversation history."""
        cursor = self.conn.cursor()
        
        try:
            # Build chat history context for follow-up questions
            history_section = ""
            if chat_history and len(chat_history) > 0:
                history_section = "\n**Previous Conversation:**\n"
                for msg in chat_history[-3:]:  # Last 3 messages for context
                    history_section += f"User: {msg.get('user', '')}\n"
                    history_section += f"Assistant: {msg.get('assistant', '')[:200]}...\n\n"
                history_section += """**IMPORTANT - Use conversation history to:**
1. Resolve pronouns: "this company" → refer to company mentioned earlier
2. Infer missing entities: "whom to contact" → use company from previous query  
3. Understand follow-ups: "attorney" → if previous was about company X, find attorney for company X
4. Track context: if user asked about Dassault, next queries likely about Dassault

"""
            
            # Add resume context if available
            resume_section = ""
            if resume_context:
                resume_section = f"""

**USER'S RESUME CONTEXT:**
{resume_context[:1000]}

Based on the resume, extract relevant skills, experience, and preferences to personalize the job search."""

            prompt = f"""You are an intelligent career advisor and SQL expert with access to comprehensive H-1B visa and job posting data. You can answer ANY question about this data.

**DATABASE SCHEMA - COMPLETE FIELD LIST:**

1. **H1B_RAW** (479,005 rows, 97 columns) - H-1B visa sponsorship data with FULL details:

**Employer Information:**
- employer_name, employer_trade_name_dba, employer_address_1, employer_address_2
- employer_city, employer_state, employer_postal_code, employer_country
- employer_province, employer_phone, employer_phone_ext
- employer_poc_first_name, employer_poc_last_name, employer_poc_middle_name
- employer_poc_job_title, employer_poc_address_1, employer_poc_address_2
- employer_poc_city, employer_poc_state, employer_poc_postal_code, employer_poc_country
- employer_poc_province, employer_poc_phone, employer_poc_phone_ext, employer_poc_email

**Job Details:**
- job_title, soc_code, soc_title, naics_code, job_order_id
- total_workers, new_employment, continued_employment, change_previous_employment
- new_concurrent_employment, change_employer, amended_petition, full_time_position

**Worksite Location:**
- worksite_city, worksite_county, worksite_state, worksite_postal_code

**Wage Information:**
- wage_rate_of_pay_from, wage_rate_of_pay_to, wage_unit_of_pay (Hour/Year/Week/Bi-Weekly/Month)
- prevailing_wage, pw_unit_of_pay, pw_wage_level (I/II/III/IV), pw_source, pw_source_year
- pw_source_other, h1b_dependent, willful_violator

**Case Processing:**
- case_number, case_status (Certified/Denied/Withdrawn), received_date, decision_date
- original_cert_date, visa_class (H-1B/E-3/H-1B1)

**Attorney/Agent Information:**
- agent_representing_employer, agent_attorney_name, agent_attorney_first_name
- agent_attorney_last_name, lawfirm_name_business_name
- agent_attorney_city, agent_attorney_state, agent_attorney_postal_code
- agent_attorney_country, agent_attorney_province, agent_attorney_phone
- agent_attorney_phone_ext, agent_attorney_email_address

**Program-Specific:**
- public_disclosure_location, support_h1b, labor_con_agree
- fy (Fiscal Year), quarter, program_designator

2. **JOBS_PROCESSED** (37,891 rows, 30+ columns) - Enhanced job postings with H-1B intelligence:

**Basic Job Info:**
- job_id, url, title, company_clean (as company), location, description
- date_posted, posted_date, days_since_posted, snippet

**Employment Details:**
- job_type (Full-time/Part-time/Contract), work_model (Remote/Hybrid/On-site)
- employment_type, department, company_size, industry

**Compensation:**
- salary_min, salary_max, currency, qualifications, benefits

**Visa & Immigration:**
- visa_category (CPT/OPT/H-1B/US-Only), h1b_sponsor (TRUE/FALSE)
- h1b_sponsored_explicit, is_new_grad_role, classification_confidence

**H-1B Metrics (from employer intelligence):**
- h1b_approval_rate, h1b_total_petitions, total_petitions, avg_approval_rate
- sponsorship_score (0-100)

**Skills & Requirements:**
- skills, experience_level, education_level, requirements
- job_category (Engineering/Data/Product/Design/etc.)

3. **EMPLOYER_INTELLIGENCE** - Company H-1B sponsorship profiles:
- employer_original, employer_clean, sponsorship_score (0-100)
- approval_rate, total_filings, total_certified, total_denied
- filings_6mo, avg_wage_offered, is_violator, risk_level

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
"top attorney in Massachusetts" → {{"intent": "contact_info", "job_title": null, "location": "Massachusetts", "company": null, "keywords": ["attorney", "contact"]}}
"compare Amazon and Microsoft" → {{"intent": "company_comparison", "job_title": null, "location": null, "company": ["Amazon", "Microsoft"], "keywords": ["compare"]}}
"analyze my resume" → {{"intent": "resume_analysis", "job_title": null, "location": null, "company": null, "keywords": ["resume", "analyze"]}}
"what jobs match my resume" → {{"intent": "job_search", "job_title": "from_resume", "location": "from_resume", "company": null, "keywords": ["match", "resume"], "resume_skills": ["skill1", "skill2"]}}
"give me career advice" → {{"intent": "career_advice", "job_title": null, "location": null, "company": null, "keywords": ["career", "advice"]}}

**Question to analyze:** "{question}"
{history_section}
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
    
    def ask(self, question: str, resume_context: str = None, chat_history: list = None) -> Dict:
        """
        Answer questions using LLM-powered SQL generation with resume awareness and conversation context.
        
        Supports ANY question about:
        - Job search, salary info, H-1B sponsorship, company comparisons, resume analysis, career advice
        
        Args:
            question: User's natural language query
            resume_context: User's resume text for personalization
            chat_history: Previous conversation for context (list of {"user": "...", "assistant": "..."})
        """
        logger.info(f"❓ Question: {question}")
        if resume_context:
            logger.info(f"📄 Resume context provided ({len(resume_context)} chars)")
        if chat_history:
            logger.info(f"💬 Chat history provided ({len(chat_history)} messages)")
        
        # Use LLM to understand intent and extract entities (with resume context and chat history)
        intent_analysis = self._analyze_intent_with_llm(question, resume_context, chat_history)
        
        logger.info(f"🧠 LLM Analysis: {intent_analysis}")
        
        # Extract entities (fallback to regex if LLM doesn't provide)
        # Use None instead of empty string for missing values
        company = intent_analysis.get('company') or self._extract_company(question) or None
        job_title = intent_analysis.get('job_title') or self._extract_job_title(question) or None
        location = intent_analysis.get('location') or self._extract_location(question) or None
        intent = intent_analysis.get('intent', 'general')
        
        # Clean up empty strings to None
        if company == '': company = None
        if job_title == '': job_title = None
        if location == '': location = None
        
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
            logger.info(f"🔀 Routing to _get_contact_info with company={company}, location={location}")
            return self._get_contact_info(company, location)
        
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
        
        # Smart fallback: Use keyword matching ONLY to redirect if LLM missed it
        # Trust LLM for everything else but help with edge cases
        else:
            q_lower = question.lower()
            
            # Visa-related job searches (OPT, CPT, H-1B jobs)
            if any(visa in q_lower for visa in ['opt', 'cpt', 'f-1', 'h-1b jobs', 'h1b jobs', 'visa jobs', 'sponsor companies']):
                logger.info(f"⚠️ LLM returned intent='{intent}' but query is visa job search - routing to job search")
                return self._search_jobs(question, job_title, location)
            
            # Salary queries without enough context
            if any(w in q_lower for w in ['salary', 'pay', 'compensation', 'wage']) and not job_title:
                logger.info(f"⚠️ Salary query without job title - need more info")
                return self._error_response("Please specify a job title (e.g., 'software engineer salary' or 'data analyst pay in Boston')")
            
            # H-1B/sponsorship queries without company
            if any(w in q_lower for w in ['h-1b', 'h1b', 'sponsor', 'visa', 'approval rate']) and 'job' not in q_lower:
                logger.info(f"⚠️ Sponsorship query - checking for company")
                if not company:
                    company = self._extract_company(question)
                if company:
                    return self._get_sponsorship_info(company)
                else:
                    return self._error_response("Please specify a company name (e.g., 'does Amazon sponsor H-1B?')")
            
            # If query has job-related keywords, assume job search (LLM fallback)
            if any(w in q_lower for w in ['job', 'jobs', 'position', 'positions', 'opening', 'openings', 
                                           'role', 'roles', 'work', 'career', 'hiring', 'internship', 
                                           'intern', 'looking for', 'find', 'search', 'show me', 'list',
                                           'engineer', 'developer', 'analyst', 'scientist', 'manager']):
                logger.info(f"⚠️ LLM returned intent='{intent}' but query has job keywords - routing to job search")
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
                # Handle non-job-related questions with helpful guidance
                return {
                    "answer": "### 🤖 Job Intelligence AI\n\nI'm specialized in helping with **career and job search queries**. Here's what I can help you with:\n\n### 🔍 Job Search\n- Find jobs, internships, and openings\n- Filter by company, location, visa status\n- Match jobs to your resume skills\n\n### 💰 Salary Information\n- Average salaries by role and location\n- Salary ranges and negotiation advice\n- Prevailing wage information\n\n### 🌐 H-1B Visa Support\n- Companies that sponsor H-1B visas\n- Approval rates and sponsorship history\n- Contact information for immigration\n\n### 🏢 Company Analysis\n- Compare companies side-by-side\n- H-1B sponsorship profiles\n- Risk assessment and recommendations\n\n### 📄 Resume & Career\n- Analyze your resume\n- Get personalized career advice\n- Find jobs matching your skills\n\n---\n\n**💡 Try asking:**\n- \"Find software engineer jobs at Amazon\"\n- \"What's the salary for data analyst in Boston?\"\n- \"Compare Google vs Microsoft for H-1B\"\n- \"Analyze my resume\" (after uploading)\n\n*For general knowledge questions, please use a general-purpose AI.*",
                    "data": [],
                    "confidence": 0.3
                }
    
    def _normalize_location_to_state(self, location: str) -> str:
        """Convert location names to state codes for H-1B database queries."""
        state_map = {
            # States
            'massachusetts': 'MA', 'california': 'CA', 'new york': 'NY', 'texas': 'TX',
            'florida': 'FL', 'illinois': 'IL', 'washington': 'WA', 'georgia': 'GA',
            'virginia': 'VA', 'north carolina': 'NC', 'new jersey': 'NJ', 'pennsylvania': 'PA',
            'ohio': 'OH', 'michigan': 'MI', 'colorado': 'CO', 'arizona': 'AZ',
            # Major cities
            'boston': 'MA', 'cambridge': 'MA',
            'san francisco': 'CA', 'san jose': 'CA', 'bay area': 'CA', 'palo alto': 'CA', 'los angeles': 'CA',
            'seattle': 'WA',
            'nyc': 'NY', 'new york city': 'NY',
            'austin': 'TX', 'dallas': 'TX', 'houston': 'TX',
            'chicago': 'IL',
            'atlanta': 'GA',
            'denver': 'CO',
            'miami': 'FL',
            'philadelphia': 'PA'
        }
        loc_lower = location.lower().strip()
        return state_map.get(loc_lower, location.upper()[:2])  # Default to first 2 chars uppercase
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number to US format: +1 (XXX) XXX-XXXX"""
        if not phone:
            return None
        
        # Remove any non-digit characters
        digits = ''.join(c for c in str(phone) if c.isdigit())
        
        # Handle 11-digit US phone numbers (starting with 1)
        if len(digits) == 11 and digits.startswith('1'):
            return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        # Handle 10-digit US phone numbers
        elif len(digits) == 10:
            return f"+1 ({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
        # Return as-is if format doesn't match
        else:
            return phone
    
    def _get_contact_info(self, company: str, location: str = None) -> Dict:
        """Get employer + attorney contact information by company or location."""
        logger.info(f"🔍 _get_contact_info called with company='{company}' (type: {type(company)}), location='{location}' (type: {type(location)})")
        
        # Handle empty strings as None
        company = company if company and company.strip() else None
        location = location if location and location.strip() else None
        
        logger.info(f"🔍 After cleaning: company={company}, location={location}")
        
        if not company and not location:
            return self._error_response("Please specify a company name or location.")
        
        cursor = self.conn.cursor()
        
        try:
            # If location provided without company, search for top attorneys in that location
            if location and not company:
                # Normalize location to state code
                state_code = self._normalize_location_to_state(location)
                logger.info(f"🔍 Normalized location '{location}' to state code '{state_code}'")
                
                sql = f"""
                SELECT 
                    lawfirm_name_business_name,
                    agent_attorney_first_name,
                    agent_attorney_last_name,
                    agent_attorney_email_address,
                    agent_attorney_phone,
                    worksite_city,
                    worksite_state,
                    COUNT(*) as total_cases,
                    SUM(CASE WHEN case_status = 'Certified' THEN 1 ELSE 0 END) as certified_cases,
                    ROUND(SUM(CASE WHEN case_status = 'Certified' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as approval_rate
                FROM RAW.H1B_RAW
                WHERE (worksite_state = '{state_code}' OR worksite_city ILIKE '%{location}%')
                  AND agent_attorney_email_address IS NOT NULL
                  AND lawfirm_name_business_name IS NOT NULL
                GROUP BY lawfirm_name_business_name, agent_attorney_first_name, agent_attorney_last_name, 
                         agent_attorney_email_address, agent_attorney_phone, worksite_city, worksite_state
                HAVING total_cases >= 10
                ORDER BY total_cases DESC, approval_rate DESC
                LIMIT 10
                """
                
                cursor.execute(sql)
                results = cursor.fetchall()
                
                if not results:
                    return self._error_response(f"No immigration attorney data found for {location}")
                
                # Format attorney list
                answer = f"### 👔 Top Immigration Attorneys in {location}\n\n"
                answer += f"Found {len(results)} top attorneys specializing in H-1B cases:\n\n"
                
                for i, data in enumerate(results[:5], 1):
                    answer += f"## {i}. {data[1]} {data[2]}\n\n"
                    answer += f"**🏢 Law Firm:** {data[0]}  \n"
                    answer += f"**📧 Email:** {data[3]}  \n"
                    if data[4]:
                        formatted_phone = self._format_phone_number(data[4])
                        answer += f"**📱 Phone:** {formatted_phone}  \n"
                    answer += f"**📍 Location:** {data[5]}, {data[6]}  \n"
                    answer += f"**📊 Cases Handled:** {data[7]} total cases  \n"
                    answer += f"**✅ Approval Rate:** {data[9]}%  \n\n"
                    answer += "---\n\n"
                
                answer += "### 💡 Next Steps\n\n"
                answer += f"1. **Contact** top-rated attorneys via email  \n"
                answer += f"2. **Mention** you need H-1B sponsorship assistance  \n"
                answer += f"3. **Ask** about their experience with your industry  \n"
                
                return {
                    "answer": answer,
                    "data": [{"law_firm": r[0], "attorney": f"{r[1]} {r[2]}", "email": r[3], "cases": r[7]} for r in results[:5]],
                    "sql_used": sql,
                    "confidence": 0.90
                }
            
            # Original company-based search
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
            FROM RAW.H1B_RAW
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
            answer = f"### 📞 Contact Information for {data[0]}\n\n"
            
            # Employer contact section
            answer += "### 🏢 Employer Immigration Contact\n\n"
            if data[1]:  # POC email
                answer += f"**📧 Email:** {data[1]}  \n"
            if data[2]:  # POC phone
                formatted_poc_phone = self._format_phone_number(data[2])
                answer += f"**📱 Phone:** {formatted_poc_phone}  \n"
            if data[3]:  # POC title
                answer += f"**👤 Title:** {data[3]}  \n"
            
            # Attorney section
            answer += "\n### 👔 Immigration Attorney Information\n\n"
            if data[4] and data[5]:  # Attorney name
                answer += f"**Name:** {data[4]} {data[5]}  \n"
            if data[6]:  # Attorney email
                answer += f"**📧 Email:** {data[6]}  \n"
            if data[7]:  # Attorney phone
                formatted_attorney_phone = self._format_phone_number(data[7])
                answer += f"**📱 Phone:** {formatted_attorney_phone}  \n"
            if data[8]:  # Law firm
                answer += f"**🏢 Law Firm:** {data[8]}  \n"
            
            # H-1B activity
            answer += f"\n### 📊 H-1B Activity\n\n"
            answer += f"**Total Filings:** {data[9]} cases in database  \n"
            
            # Next steps
            answer += "\n### ✅ Next Steps\n\n"
            answer += f"1. **Email** {data[1] or data[6] or 'company HR'} to inquire about H-1B sponsorship  \n"
            answer += "2. **Mention** you're on F-1 visa seeking sponsorship  \n"
            answer += "3. **Attach** your resume and highlight relevant experience  \n"
            
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
            FROM RAW.H1B_RAW
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
            
            # Format numbers properly to avoid markdown issues
            avg_salary = f"${int(data[4]):,}"
            min_salary = f"${int(data[5]):,}"
            max_salary = f"${int(data[6]):,}"
            prevailing_wage = f"${int(data[7]):,}"
            
            answer = f"### 💼 Salary Data for {data[0]}\n\n"
            if location:
                answer += f"**📍 Location:** {location_str}  \n"
            answer += f"**📊 Sample Size:** {data[3]} H-1B cases\n\n"
            
            answer += f"**💰 Average Salary:** {avg_salary}  \n"
            answer += f"**📊 Salary Range:** {min_salary} - {max_salary}  \n"
            answer += f"**📈 Prevailing Wage:** {prevailing_wage}  \n"
            
            # Negotiation advice
            answer += "\n### 💡 Negotiation Advice\n\n"
            if data[4] < data[7]:
                gap = f"${int(data[7] - data[4]):,}"
                answer += f"- **Target:** {prevailing_wage} (prevailing wage)  \n"
                answer += f"- Current average is {gap} below market  \n"
            else:
                competitive_low = f"${int(data[4]*0.9):,}"
                competitive_high = f"${int(data[4]*1.1):,}"
                answer += f"- **Competitive range:** {competitive_low} - {competitive_high}  \n"
            
            answer += f"- **Minimum acceptable:** {prevailing_wage} (prevailing wage floor)  \n"
            
            # Show other locations if available
            if len(results) > 1:
                answer += f"\n### 📍 Other Locations\n\n"
                for row in results[1:4]:
                    loc = f"{row[1]}, {row[2]}" if row[1] else row[2]
                    loc_avg = f"${int(row[4]):,}"
                    answer += f"- **{loc}:** {loc_avg} avg ({row[3]} cases)  \n"
            
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
                risk_level,
                -- Calculate REAL approval rate: certified / total filings
                ROUND(total_certified * 100.0 / NULLIF(total_filings, 0), 2) as real_approval_rate
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
            answer = f"### 🏢 {data[0]} - H-1B Sponsorship Profile\n\n"
            
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
            
            answer += f"### {badge} Sponsor\n\n"
            answer += f"**Overall Score:** {score:.1f}/100  \n\n"
            
            # Statistics - Use REAL approval rate (index 10)
            real_approval_rate = data[10] if len(data) > 10 else (data[4] / data[3] * 100 if data[3] > 0 else 0)
            answer += f"### 📊 Statistics (FY2025 Q3)\n\n"
            answer += f"**✅ Approval Rate:** {real_approval_rate:.1f}%  \n"
            answer += f"**📋 Total Filings:** {data[3]:,}  \n"
            answer += f"**✔️ Certified:** {data[4]:,}  \n"
            answer += f"**❌ Denied:** {data[5]:,}  \n"
            answer += f"**📈 Recent Activity:** {data[6]:,} filings in last 6 months  \n"
            
            # Format salary properly
            avg_salary = f"${int(data[7]):,}"
            answer += f"**💰 Average Salary Offered:** {avg_salary}  \n"
            
            # Risk assessment
            answer += f"\n### ⚠️ Risk Assessment\n\n"
            answer += f"**Risk Level:** {data[9]}  \n"
            if data[8]:  # is_violator
                answer += "**⛔ WARNING:** Willful violator on record  \n"
            
            # Recommendation
            answer += "\n### 💡 Recommendation\n\n"
            if score >= 80:
                answer += "✅ **Highly recommended** - Strong sponsorship history  \n"
            elif score >= 60:
                answer += "✓ **Good option** - Reliable sponsor  \n"
            elif score >= 40:
                answer += "⚠️ **Proceed with caution** - Limited history  \n"
            else:
                answer += "🚫 **Not recommended** - High risk  \n"
            
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
                filings_6mo,
                total_certified,
                -- Calculate REAL approval rate
                ROUND(total_certified * 100.0 / NULLIF(total_filings, 0), 2) as real_approval_rate
            FROM processed.employer_intelligence
            WHERE {conditions}
            ORDER BY sponsorship_score DESC
            """
            
            cursor.execute(sql)
            results = cursor.fetchall()
            
            if not results:
                return self._error_response(f"No data found for companies: {', '.join(companies)}")
            
            # Format comparison
            answer = f"### 📊 H-1B Sponsorship Comparison\n\n"
            
            for i, data in enumerate(results, 1):
                # Add rank emoji
                rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                # Use real approval rate (index 8)
                real_rate = data[8] if len(data) > 8 else (data[7] / data[3] * 100 if data[3] > 0 else 0)
                answer += f"## {rank_emoji} {i}. {data[0]}\n\n"
                answer += f"**📈 Sponsorship Score:** {data[1]:.1f}/100  \n"
                answer += f"**✅ Approval Rate:** {real_rate:.1f}%  \n"
                answer += f"**📋 Total Filings:** {data[3]:,}  \n"
                
                # Format salary
                avg_salary = f"${int(data[4]):,}"
                answer += f"**💰 Average Salary:** {avg_salary}  \n"
                answer += f"**⚠️ Risk Level:** {data[5]}  \n"
                answer += f"**📈 Recent Activity:** {data[6]:,} filings in 6 months  \n\n"
                answer += "---\n\n"
            
            # Winner
            if len(results) >= 2:
                winner = results[0]
                answer += f"### 🏆 Best Choice: {winner[0]}\n\n"
                score_diff = winner[1] - results[1][1]
                approval_diff = (winner[2] - results[1][2]) * 100
                answer += f"**Why?** Higher score (+{score_diff:.1f} points), "
                answer += f"better approval rate (+{approval_diff:.1f}%)  \n"
            
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
                
                answer = f"### 🎯 Found {total_available} jobs (showing {len(jobs)})\n\n"
                
                for i, job in enumerate(jobs, 1):
                    # Title with bold formatting
                    answer += f"### {i}. {job['TITLE']}\n\n"
                    
                    # Company and Location on one line
                    answer += f"**🏢 Company:** {job['COMPANY']}  \n"
                    answer += f"**📍 Location:** {job['LOCATION']}  \n"
                    
                    # Visa category with color coding
                    visa = job['VISA_CATEGORY']
                    answer += f"**🎫 Visa Status:** {visa}  \n"
                    
                    # Salary if available
                    if job.get('SALARY_MIN') and job.get('SALARY_MAX'):
                        answer += f"**💰 Salary Range:** ${job['SALARY_MIN']:,} - ${job['SALARY_MAX']:,}  \n"
                    
                    # Work model if available
                    if job.get('WORK_MODEL'):
                        answer += f"**💼 Work Model:** {job['WORK_MODEL']}  \n"
                    
                    # H-1B sponsorship info
                    if job.get('H1B_SPONSOR'):
                        # Try both field names for backward compatibility
                        approval_rate_val = job.get('H1B_APPROVAL_RATE') or job.get('AVG_APPROVAL_RATE')
                        if approval_rate_val:
                            approval_rate = approval_rate_val * 100
                            answer += f"**✅ H-1B Sponsor:** Yes ({approval_rate:.0f}% approval rate)  \n"
                        else:
                            answer += f"**✅ H-1B Sponsor:** Yes  \n"
                    
                    # Days since posted
                    if job.get('DAYS_SINCE_POSTED') is not None:
                        days = job['DAYS_SINCE_POSTED']
                        if days == 0:
                            answer += f"**📅 Posted:** Today  \n"
                        elif days == 1:
                            answer += f"**📅 Posted:** Yesterday  \n"
                        elif days <= 7:
                            answer += f"**📅 Posted:** {days} days ago  \n"
                    
                    # Apply link as button-style with fallback
                    job_url = job.get('URL', '').strip()
                    if job_url and job_url.startswith('http'):
                        answer += f"\n**[🔗 Apply Now]({job_url})**\n\n"
                    else:
                        # Generate search URL if no direct URL available
                        company = job['COMPANY'].replace(' ', '+')
                        title = job['TITLE'].replace(' ', '+')
                        search_url = f"https://www.google.com/search?q={company}+{title}+jobs"
                        answer += f"\n**[🔗 Search Job]({search_url})**\n\n"
                    
                    # Divider between jobs
                    answer += "---\n\n"
                
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
        
        return None
    
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
        return None
    
    def _extract_location(self, text: str) -> str:
        """Extract location."""
        locations = ['boston', 'new york', 'nyc', 'san francisco', 'seattle', 'austin',
                    'chicago', 'denver', 'los angeles', 'la', 'bay area', 'remote']
        
        t = text.lower()
        for loc in locations:
            if loc in t:
                return loc
        return None
    
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