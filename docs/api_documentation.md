# API Integration Examples for P3

## Endpoint 1: Job Search (Agent 1)

from fastapi import APIRouter, Query, HTTPException
import sys
sys.path.append('../../')
from snowflake.agents.agent1_search import JobSearchAgent

router = APIRouter()

@router.get("/api/search")
async def search_jobs(
    query: str = Query(..., min_length=1, max_length=500),
    visa_status: str = Query(None),
    location: str = Query(None),
    salary_min: int = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Search jobs with Agent 1."""
    agent = JobSearchAgent()
    
    try:
        filters = {}
        if visa_status:
            filters['visa_status'] = visa_status
        if location:
            filters['location'] = location
        if salary_min:
            filters['salary_min'] = salary_min
        filters['limit'] = limit
        
        result = agent.search(query, filters)
        
        if result['status'] == 'success':
            return {
                "query": result['query'],
                "total": result['total'],
                "jobs": result['jobs']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    finally:
        agent.close()


## Endpoint 2: Resume Match (Agent 4)

from fastapi import UploadFile, File
from snowflake.agents.agent4_matcher import ResumeMatcherAgent
import PyPDF2
import io

@router.post("/api/resume/match")
async def match_resume(file: UploadFile = File(...)):
    """Match resume to jobs using Agent 4."""
    
    # Extract text from PDF
    pdf_bytes = await file.read()
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    
    resume_text = ""
    for page in pdf_reader.pages:
        resume_text += page.extract_text()
    
    # Match using Agent 4
    matcher = ResumeMatcherAgent()
    
    try:
        import uuid
        resume_id = str(uuid.uuid4())
        
        result = matcher.match_resume(resume_id, resume_text)
        
        return {
            "resume_id": resume_id,
            "profile": result['profile'],
            "top_matches": result['top_matches'],
            "total_candidates": result['total_candidates']
        }
        
    finally:
        matcher.close()


## Endpoint 3: Classify Single Job (Agent 3)

from snowflake.agents.agent3_classifier import VisaClassifier

@router.post("/api/classify")
async def classify_job(
    title: str,
    company: str,
    description: str
):
    """Classify a single job using Agent 3."""
    classifier = VisaClassifier()
    
    try:
        result = classifier.classify_job({
            'title': title,
            'company': company,
            'description': description
        })
        
        return {
            "visa_category": result['visa_category'],
            "confidence": result['confidence'],
            "signals": result['signals']
        }
        
    finally:
        classifier.close()