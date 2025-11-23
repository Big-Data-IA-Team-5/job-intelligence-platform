-- Job Intelligence Mart
-- Final fact table for analytics and application queries

{{
    config(
        materialized='table',
        schema='marts'
    )
}}

WITH jobs AS (
    SELECT * FROM {{ ref('embedded_jobs') }}
),

enriched AS (
    SELECT
        -- Identifiers
        job_id,
        source,
        url,
        
        -- Job details
        title,
        company_name,
        location,
        description,
        job_type,
        seniority_level,
        job_category,
        extracted_skills,
        
        -- Dates
        posted_date,
        scraped_at,
        
        -- Compensation
        salary_range,
        prevailing_wage,
        
        -- H1B information
        likely_sponsors_h1b,
        h1b_employer_name,
        h1b_job_title,
        h1b_application_count,
        
        -- Flags
        is_remote,
        
        -- Embeddings for semantic search
        description_embedding,
        skills_embedding,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS mart_created_at
        
    FROM jobs
)

SELECT * FROM enriched
