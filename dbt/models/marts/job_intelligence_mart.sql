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
        company,
        location,
        description,
        snippet,
        job_type,
        
        -- Dates
        posted_date,
        scraped_at,
        
        -- Compensation
        salary_min,
        salary_max,
        salary_text,
        
        -- H1B information
        h1b_sponsor,
        h1b_employer_name,
        h1b_city,
        h1b_state,
        total_petitions,
        avg_approval_rate,
        
        -- Embeddings for semantic search (stored as VARIANT)
        description_embedding,
        
        -- Metadata
        CURRENT_TIMESTAMP() AS mart_created_at
        
    FROM jobs
)

SELECT * FROM enriched