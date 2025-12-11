"""
Chat API endpoint for Agent 2 with LLM-Powered Intent Detection
"""
from fastapi import APIRouter, HTTPException
import sys
from pathlib import Path
import snowflake.connector
import os
from dotenv import load_dotenv
import json
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from snowflake.agents.agent2_chat import JobIntelligenceAgent

load_dotenv('config/.env')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Store conversation context in memory (in production, use Redis/database)
conversation_history = {}


from pydantic import BaseModel
from typing import Optional, List, Dict

class ChatRequest(BaseModel):
    question: str
    job_role: Optional[str] = None
    resume_text: Optional[str] = None
    user_id: str = "anonymous"
    chat_history: Optional[List[Dict]] = None

@router.post("/ask")
async def ask_question(request: ChatRequest):
    """
    Intelligent chat endpoint powered by Agent 2's LLM reasoning.
    
    Agent 2 has full intelligence with:
    - Complete database schema awareness (H1B_RAW, JOBS_PROCESSED, EMPLOYER_INTELLIGENCE)
    - LLM-powered intent detection (job_search, salary_info, h1b_sponsorship, etc.)
    - Resume context integration for personalized matching
    - Entity extraction (job_title, location, company, skills)
    - Multi-intent routing (job search, salary analysis, H-1B sponsorship, contact info, comparisons)
    
    This endpoint simply passes requests to Agent 2's intelligence.
    
    Parameters:
    - question: User's natural language query
    - resume_text: User's resume text for context (persists in conversation)
    - user_id: User identifier for conversation tracking
    - chat_history: Previous conversation context
    
    Examples:
    - "data engineer jobs in Boston" → Agent 2 detects job_search, extracts entities, calls Agent 1
    - "what's the salary for SDE at Amazon?" → Agent 2 detects salary_info, queries H-1B data
    - "compare Google vs Microsoft" → Agent 2 detects company_comparison, analyzes both
    - "who should I contact at Amazon?" → Agent 2 detects contact_info, retrieves POC details
    """
    if not request.question or len(request.question.strip()) < 3:
        raise HTTPException(400, "Question too short")
    
    # Store conversation history AND resume context for user
    if request.user_id not in conversation_history:
        conversation_history[request.user_id] = []
    
    logger.info(f"🔍 User {request.user_id} asked: '{request.question}'")
    
    if request.resume_text:
        logger.info(f"📄 Resume context provided ({len(request.resume_text)} chars)")
    
    # Use chat_history from request if provided, otherwise use stored history
    # Check if None specifically (not empty list), since [] is a valid empty history
    chat_hist = request.chat_history if request.chat_history is not None else conversation_history.get(request.user_id, [])
    logger.info(f"💬 Using chat history: {len(chat_hist)} messages (from {'request' if request.chat_history is not None else 'memory'})")
    
    agent = JobIntelligenceAgent()
    
    try:
        # Agent 2 handles ALL intelligence - intent detection, entity extraction, routing
        # Resume text is passed and persists in conversation context
        # Use chat_history from frontend (context manager) for better context awareness
        # Enable debug info for frontend AI intelligence display
        result = agent.ask(request.question, resume_context=request.resume_text, chat_history=chat_hist, return_debug=True)
        
        # Store interaction for future context (merge with incoming history if provided)
        current_turn = {
            "user": request.question,
            "assistant": result['answer'][:500],
            "has_resume": bool(request.resume_text)  # Track if resume was present
        }
        
        # If chat_history was provided in request, use it as base and add current turn
        if request.chat_history is not None:
            conversation_history[request.user_id] = request.chat_history[-9:] + [current_turn]
        else:
            conversation_history[request.user_id].append(current_turn)
            # Keep last 10 interactions
            if len(conversation_history[request.user_id]) > 10:
                conversation_history[request.user_id] = conversation_history[request.user_id][-10:]
        
        # Return response with debug_info for AI intelligence display
        response = {
            "question": request.question,
            "answer": result['answer'],
            "data_points": len(result.get('data', [])),
            "confidence": result.get('confidence', 0.0),
            "sources": result.get('sources', [])
        }
        
        # Include debug_info if present (for AI intelligence display in frontend)
        if 'debug_info' in result:
            response['debug_info'] = result['debug_info']
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
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