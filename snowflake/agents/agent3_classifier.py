"""
Snowflake Cortex Agent 3: Job Classifier
Uses Cortex Complete to classify jobs into categories
"""

def classify_job(title: str, description: str) -> dict:
    """
    Classify a job posting into category, seniority, and extract key information
    
    Args:
        title: Job title
        description: Job description
        
    Returns:
        Dictionary with classification results
    """
    
    # This function would be deployed as a Snowflake Python UDF
    # Using Cortex Complete for classification
    
    import snowflake.snowpark as snowpark
    from snowflake.snowpark.functions import col
    from snowflake.cortex import Complete
    
    prompt = f"""
    Analyze this job posting and provide structured information:
    
    Title: {title}
    Description: {description[:1000]}
    
    Provide:
    1. Category (Engineering, Data, Product, Design, Sales, Marketing, Operations, Other)
    2. Seniority Level (Junior, Mid-Level, Senior, Principal, Management)
    3. Top 5 Required Skills (comma-separated)
    4. Whether it's remote-friendly (Yes/No)
    5. Estimated education requirement (High School, Bachelor's, Master's, PhD, Not Specified)
    
    Format your response as JSON with keys: category, seniority, skills, remote, education
    """
    
    result = Complete(
        model='mistral-large',
        prompt=prompt,
        options={'temperature': 0.1}
    )
    
    return result


# SQL to create the UDF in Snowflake:
"""
CREATE OR REPLACE FUNCTION CLASSIFY_JOB(title STRING, description STRING)
RETURNS OBJECT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.9'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'classify_job'
AS
$$
[Include the classify_job function code here]
$$;
"""

# Example usage:
"""
SELECT 
    job_id,
    title,
    CLASSIFY_JOB(title, description) as classification
FROM RAW.JOBS
WHERE scraped_at >= CURRENT_DATE - 1;
"""
