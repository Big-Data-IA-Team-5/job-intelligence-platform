"""
Chat API endpoint for Agent 2 with Smart Intent Detection
"""
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path
import re

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from snowflake.agents.agent2_chat import JobIntelligenceAgent

router = APIRouter()


def detect_intent(query: str) -> str:
    """
    Detect user intent: 'job_search' or 'question'
    
    Job search indicators:
    - Job titles (engineer, developer, analyst, manager, etc.)
    - Action words (looking for, need, want, hire, apply)
    - Job-related keywords (position, role, opening, vacancy)
    
    Question indicators:
    - Question words (who, what, where, when, how, which)
    - Comparison words (vs, versus, compare, better)
    - Information requests (tell me, show me, give me)
    """
    query_lower = query.lower().strip()
    
    # Very short queries - likely job search
    if len(query_lower.split()) <= 3:
        # Check if it's a simple job title search
        job_keywords = ['engineer', 'developer', 'analyst', 'scientist', 'manager', 'designer',
                       'consultant', 'specialist', 'coordinator', 'director', 'architect',
                       'intern', 'job', 'jobs', 'position', 'role', 'opening']
        if any(keyword in query_lower for keyword in job_keywords):
            return "job_search"
    
    # Strong question indicators (must start with or contain question words)
    question_starters = [
        r'^(who|what|where|when|why|how|which|does|is|can|should|tell|give|show)',
        r'\b(contact|email|phone|reach|attorney|lawyer|firm)\b',
        r'\bsalary\s+(for|of|at|range)\b',
        r'\b(approval rate|petition|compare|versus|vs|better|difference)\b',
        r'\b(does .* sponsor|is .* safe|should i)\b',
    ]
    
    # Job search indicators (more specific patterns)
    job_search_patterns = [
        r'\b(software|data|machine learning|full stack|backend|frontend|devops|cloud)\s+(engineer|developer|scientist|analyst)\b',
        r'\b(product|project|program|engineering|technical)\s+manager\b',
        r'\b(looking for|need|want|searching for|find|apply)\s+(a |an )?(job|position|role|work)\b',
        r'\bjob[s]?\s+(at|in|for|with)\b',
        r'\b(entry level|new grad|junior|senior|lead|principal|staff)\s+(engineer|developer|position|role)\b',
        r'\b(remote|hybrid|onsite)\s+(job|position|role|work)\b',
        r'\b(intern|internship)\b',
    ]
    
    # Calculate scores
    question_score = sum(1 for pattern in question_starters if re.search(pattern, query_lower))
    job_search_score = sum(1 for pattern in job_search_patterns if re.search(pattern, query_lower))
    
    # Strong question indicator (starts with question word or has contact/salary keywords)
    if question_score >= 2:
        return "question"
    
    # Clear job search indicators
    if job_search_score > 0:
        return "job_search"
    
    # If starts with question word, it's a question
    if re.match(r'^(who|what|where|when|why|how|which|does|is|can|should)', query_lower):
        return "question"
    
    # Check for simple job title mentions (default to job search)
    simple_job_titles = ['engineer', 'developer', 'analyst', 'scientist', 'manager', 'designer', 
                         'consultant', 'specialist', 'coordinator', 'director', 'architect',
                         'intern', 'internship']
    
    if any(title in query_lower for title in simple_job_titles):
        return "job_search"
    
    # Default to question for ambiguous queries
    return "question"


@router.post("/ask")
async def ask_question(question: str, job_role: str = None, resume_context: str = None):
    """
    Ask any question about jobs, H-1B, salaries, sponsorship.
    
    Examples:
    - "Who to contact at Amazon for H-1B?"
    - "What salary for Software Engineer in Seattle?"
    - "Does Google sponsor H-1B?"
    - "Compare Amazon vs Microsoft"
    
    Optional parameters:
    - job_role: Pre-extracted job titles from LLM
    - resume_context: User's resume text for personalized recommendations
    
    Returns natural language answer with data sources.
    """
    if not question or len(question.strip()) < 3:
        raise HTTPException(400, "Question too short")
    
    agent = JobIntelligenceAgent()
    
    try:
        # If job_role provided, inject it into the question context
        # This helps Agent 2 extract the job title correctly
        if job_role:
            # Ensure the job role is mentioned in the question
            if job_role.lower() not in question.lower():
                question = f"{question} (Job: {job_role})"
        
        # Pass resume_context to agent for personalized responses
        result = agent.ask(question, resume_context=resume_context)
        
        return {
            "question": question,
            "answer": result['answer'],
            "data_points": len(result.get('data', [])),
            "confidence": result.get('confidence', 0.0),
            "sources": result.get('sources', [])
        }
        
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")
    
    finally:
        agent.close()


@router.post("/parse")
async def parse_query_with_llm(query: str):
    """
    Use Snowflake Cortex LLM to intelligently parse user query.
    Extracts job role, intent, and reformulates question if needed.
    
    Examples:
    - "give me average salary of SDE role and jobs" 
      → job_role: "Software Development Engineer", clean_query: "What is the average salary for Software Development Engineer?"
    - "ML engineer compensation"
      → job_role: "Machine Learning Engineer", clean_query: "What is the compensation for Machine Learning Engineer?"
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(400, "Query too short")
    
    import snowflake.connector
    import os
    from dotenv import load_dotenv
    
    load_dotenv('config/.env')
    
    try:
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            database='job_intelligence',
            schema='processed',
            warehouse='compute_wh'
        )
        
        cursor = conn.cursor()
        
        # Use Snowflake Cortex LLM to parse the query
        llm_query = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large2',
            CONCAT(
                'Extract information from this job search query. Return ONLY a JSON object with these fields:\\n',
                '1. job_role: The standard job title using common industry terms. Common titles include:\\n',
                '   - Software Engineer (NOT Software Development Engineer)\\n',
                '   - Data Engineer, Data Scientist, Data Analyst\\n',
                '   - Machine Learning Engineer\\n',
                '   - Product Manager\\n',
                '   - Frontend Developer, Backend Developer, Full Stack Developer\\n',
                '   Convert abbreviations: SDE->Software Engineer, ML->Machine Learning, DS->Data Scientist\\n',
                '2. has_question: true if asking about salary/pay/contact/who/what, false if just searching jobs\\n',
                '3. clean_query: If has_question is true, reformulate as a clear question using the job_role.\\n',
                '4. search_term: The job_role for searching\\n\\n',
                'Query: "{query}"\\n\\n',
                'Return only valid JSON, no other text. Use standard job titles.'
            )
        ) as llm_response
        """
        
        cursor.execute(llm_query)
        result = cursor.fetchone()
        
        if result and result[0]:
            # Parse LLM response
            llm_response = result[0]
            
            # Try to extract JSON from response
            try:
                # Sometimes LLM wraps in markdown code blocks
                if '```json' in llm_response:
                    llm_response = llm_response.split('```json')[1].split('```')[0]
                elif '```' in llm_response:
                    llm_response = llm_response.split('```')[1].split('```')[0]
                
                import json
                parsed = json.loads(llm_response.strip())
                
                cursor.close()
                conn.close()
                
                return {
                    "original_query": query,
                    "job_role": parsed.get("job_role", ""),
                    "has_question": parsed.get("has_question", False),
                    "clean_query": parsed.get("clean_query", query),
                    "search_term": parsed.get("search_term", parsed.get("job_role", query)),
                    "success": True
                }
            except:
                # Fallback if JSON parsing fails
                cursor.close()
                conn.close()
                return {
                    "original_query": query,
                    "job_role": "",
                    "has_question": False,
                    "clean_query": query,
                    "search_term": query,
                    "success": False
                }
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        raise HTTPException(500, f"LLM parsing failed: {str(e)}")
    
    return {
        "original_query": query,
        "job_role": "",
        "has_question": False,
        "clean_query": query,
        "search_term": query,
        "success": False
    }


@router.post("/smart")
async def smart_query(query: str):
    """
    Smart endpoint that automatically detects intent and routes to either:
    - Job search (returns job listings)
    - AI chat (returns insights/answers)
    
    Examples:
    - "software engineer at Google" → Job Search
    - "Who to contact at Amazon for H-1B?" → AI Chat
    - "data scientist remote" → Job Search
    - "What's the salary for engineers?" → AI Chat
    """
    if not query or len(query.strip()) < 2:
        raise HTTPException(400, "Query too short")
    
    intent = detect_intent(query)
    
    return {
        "query": query,
        "intent": intent,
        "action": "search_jobs" if intent == "job_search" else "ask_ai",
        "message": f"Detected as: {'Job Search' if intent == 'job_search' else 'AI Question'}"
    }


@router.get("/examples")
async def get_example_questions():
    """Get example questions users can ask."""
    return {
        "examples": [
            {
                "category": "Contact Information",
                "questions": [
                    "Who should I contact at Microsoft for H-1B?",
                    "Which law firm does Google use for immigration?",
                    "Give me attorney email for Amazon H-1B cases"
                ]
            },
            {
                "category": "Salary Intelligence",
                "questions": [
                    "What's the salary for Data Engineer in Boston?",
                    "How much do Software Engineers make in Seattle?",
                    "Salary range for Machine Learning Engineer in SF?"
                ]
            },
            {
                "category": "Sponsorship Analysis",
                "questions": [
                    "Does Netflix sponsor H-1B visas?",
                    "What's Apple's H-1B approval rate?",
                    "Is Uber safe for H-1B sponsorship?"
                ]
            },
            {
                "category": "Company Comparison",
                "questions": [
                    "Compare Amazon vs Google for H-1B",
                    "Meta vs Microsoft sponsorship",
                    "Which is better: Stripe or Snowflake for H-1B?"
                ]
            }
        ]
    }