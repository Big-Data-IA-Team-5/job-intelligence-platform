"""
Snowflake Cortex Agent 4: Resume-Job Matcher
Matches resumes with job postings using semantic similarity
"""

def match_resume_to_jobs(
    resume_embedding: list,
    top_k: int = 10,
    min_similarity: float = 0.7
) -> list:
    """
    Find best matching jobs for a resume using vector similarity
    
    Args:
        resume_embedding: Vector embedding of resume
        top_k: Number of top matches to return
        min_similarity: Minimum similarity threshold
        
    Returns:
        List of matching job dictionaries with similarity scores
    """
    
    # This would be deployed as a Snowflake Python UDF or UDTF
    
    import snowflake.snowpark as snowpark
    from snowflake.snowpark.functions import col, lit
    from snowflake.cortex import EmbedText768
    
    # SQL implementation using vector similarity
    query = f"""
    WITH resume_vector AS (
        SELECT {resume_embedding} AS embedding
    ),
    similarities AS (
        SELECT 
            j.job_id,
            j.title,
            j.company_name,
            j.location,
            j.description,
            j.salary_range,
            j.likely_sponsors_h1b,
            j.is_remote,
            j.extracted_skills,
            -- Cosine similarity between resume and job
            VECTOR_COSINE_SIMILARITY(
                r.embedding,
                j.description_embedding
            ) AS similarity_score
        FROM MARTS.JOB_INTELLIGENCE_MART j
        CROSS JOIN resume_vector r
        WHERE j.posted_date >= CURRENT_DATE - 30
    )
    SELECT *
    FROM similarities
    WHERE similarity_score >= {min_similarity}
    ORDER BY similarity_score DESC
    LIMIT {top_k};
    """
    
    return query


def extract_resume_skills(resume_text: str) -> dict:
    """
    Extract skills and key information from resume
    
    Args:
        resume_text: Full text of resume
        
    Returns:
        Dictionary with extracted information
    """
    
    import snowflake.cortex as cortex
    
    prompt = f"""
    Analyze this resume and extract:
    1. Top 10 technical skills
    2. Years of experience (estimate)
    3. Education level
    4. Job titles/roles held
    5. Industries worked in
    
    Resume:
    {resume_text[:2000]}
    
    Provide response as JSON with keys: skills, experience_years, education, roles, industries
    """
    
    result = cortex.Complete(
        model='mistral-large',
        prompt=prompt,
        options={'temperature': 0.1}
    )
    
    return result


# SQL to create matching function:
"""
CREATE OR REPLACE FUNCTION MATCH_RESUME_TO_JOBS(
    resume_embedding VECTOR(FLOAT, 768),
    top_k INTEGER DEFAULT 10,
    min_similarity FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    job_id STRING,
    title STRING,
    company_name STRING,
    similarity_score FLOAT
)
AS
$$
    SELECT 
        j.job_id,
        j.title,
        j.company_name,
        j.location,
        j.salary_range,
        j.url,
        VECTOR_COSINE_SIMILARITY(resume_embedding, j.description_embedding) AS similarity_score
    FROM MARTS.JOB_INTELLIGENCE_MART j
    WHERE j.posted_date >= CURRENT_DATE - 30
        AND VECTOR_COSINE_SIMILARITY(resume_embedding, j.description_embedding) >= min_similarity
    ORDER BY similarity_score DESC
    LIMIT top_k
$$;

-- Example usage:
SELECT *
FROM TABLE(MATCH_RESUME_TO_JOBS(
    (SELECT resume_embedding FROM MARTS.USER_RESUMES WHERE user_id = 'user123' LIMIT 1),
    10,
    0.7
));
"""
