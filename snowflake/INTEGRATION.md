# Agent 1 Integration Guide (For P3)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r snowflake/requirements.txt
```

### 2. Use in FastAPI

**In `backend/app/routes/search.py`:**
```python
from fastapi import APIRouter, Query
import sys
sys.path.append('../../')
from snowflake.agents.agent1_search import JobSearchAgent

router = APIRouter()

@router.get("/api/search")
async def search_jobs(
    query: str = Query(..., description="Natural language query"),
    visa_status: str = Query(None),
    location: str = Query(None),
    salary_min: int = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    agent = JobSearchAgent()
    
    filters = {}
    if visa_status:
        filters['visa_status'] = visa_status
    if location:
        filters['location'] = location
    if salary_min:
        filters['salary_min'] = salary_min
    filters['limit'] = limit
    
    result = agent.search(query, filters)
    agent.close()
    
    if result['status'] == 'success':
        return {
            "query": result['query'],
            "total": result['total'],
            "jobs": result['jobs']
        }
    else:
        raise HTTPException(status_code=500, detail=result['error'])
```

## API Response Format
```json
{
  "status": "success",
  "query": "CPT internships in Boston",
  "sql": "SELECT ... WHERE ...",
  "jobs": [
    {
      "JOB_ID": "test_001",
      "TITLE": "Software Engineer Intern",
      "COMPANY": "Microsoft",
      "LOCATION": "Boston, MA",
      "SALARY_MIN": 60000,
      "SALARY_MAX": 80000,
      "VISA_CATEGORY": "CPT",
      "H1B_SPONSOR": false
    }
  ],
  "total": 1
}
```

## Example Queries

| Query | Expected Result |
|-------|----------------|
| "Show me all jobs" | All jobs |
| "CPT internships in Boston" | CPT + Boston |
| "Find H-1B sponsors" | H-1B sponsors |
| "Data engineer jobs" | Engineer titles |
| "Remote software positions" | Remote + software |

## Error Handling
```python
result = agent.search(query)

if result['status'] == 'error':
    # Handle error
    print(f"Error: {result['error']}")
```

## Tips
- Always close agent after use: `agent.close()`
- Use filters for structured queries
- Query is case-insensitive
- Location supports partial matching