"""
Resume Routes
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.models.schemas import (
    ResumeUploadRequest, ResumeMatchRequest, 
    ResumeMatchResponse, JobMatch, JobDetail
)
from app.utils.snowflake_client import get_snowflake_client

router = APIRouter()


@router.post("/upload")
async def upload_resume(request: ResumeUploadRequest):
    """
    Upload and process a resume
    """
    try:
        client = get_snowflake_client()
        
        # Generate embedding for resume
        embed_query = """
        SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', %s) AS resume_embedding
        """
        
        embedding_df = client.execute_query(embed_query, [request.resume_text])
        resume_embedding = embedding_df['RESUME_EMBEDDING'].iloc[0]
        
        # Extract skills using Cortex
        skills_query = """
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large',
            CONCAT('Extract top 10 technical skills from this resume as comma-separated list: ', %s)
        ) AS skills
        """
        
        skills_df = client.execute_query(skills_query, [request.resume_text[:2000]])
        skills = skills_df['SKILLS'].iloc[0]
        
        # Store resume
        insert_query = """
        INSERT INTO MARTS.USER_RESUMES (user_id, resume_text, resume_embedding, skills)
        VALUES (%s, %s, %s, %s)
        """
        
        client.execute_query(
            insert_query, 
            [request.user_id, request.resume_text, resume_embedding, skills]
        )
        
        return {
            "message": "Resume uploaded successfully",
            "user_id": request.user_id,
            "extracted_skills": skills
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match", response_model=ResumeMatchResponse)
async def match_resume(request: ResumeMatchRequest):
    """
    Find matching jobs for a resume
    """
    try:
        client = get_snowflake_client()
        
        # Get resume embedding
        resume_query = """
        SELECT resume_embedding 
        FROM MARTS.USER_RESUMES 
        WHERE resume_id = %s
        """
        
        resume_df = client.execute_query(resume_query, [request.resume_id])
        
        if resume_df.empty:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        resume_embedding = resume_df['RESUME_EMBEDDING'].iloc[0]
        
        # Find matching jobs
        match_query = """
        SELECT 
            job_id, source, title, company_name, location, description,
            posted_date, url, job_type, salary_range, seniority_level,
            job_category, extracted_skills, is_remote, likely_sponsors_h1b,
            h1b_employer_name, h1b_application_count, prevailing_wage,
            VECTOR_COSINE_SIMILARITY(description_embedding, %s) AS similarity_score
        FROM MARTS.JOB_INTELLIGENCE_MART
        WHERE posted_date >= CURRENT_DATE - 30
            AND VECTOR_COSINE_SIMILARITY(description_embedding, %s) >= %s
        ORDER BY similarity_score DESC
        LIMIT %s
        """
        
        df = client.execute_query(
            match_query, 
            [resume_embedding, resume_embedding, request.min_similarity, request.top_k]
        )
        
        matches = []
        for _, row in df.iterrows():
            job = JobDetail(**{k: v for k, v in row.items() if k != 'similarity_score'})
            matches.append(JobMatch(job=job, similarity_score=row['similarity_score']))
        
        return ResumeMatchResponse(
            matches=matches,
            resume_id=request.resume_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}")
async def get_user_resumes(user_id: str):
    """
    Get all resumes for a user
    """
    try:
        client = get_snowflake_client()
        
        query = """
        SELECT resume_id, skills, uploaded_at
        FROM MARTS.USER_RESUMES
        WHERE user_id = %s
        ORDER BY uploaded_at DESC
        """
        
        df = client.execute_query(query, [user_id])
        
        return {"resumes": df.to_dict('records')}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
