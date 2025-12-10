-- Embedded Jobs
-- Generates vector embeddings for semantic search
-- VECTOR types treated as VARIANT for dbt compatibility

{{
    config(
        materialized='incremental',
        unique_key='job_id',
        schema='processing',
        incremental_strategy='merge',
        merge_update_columns=['title', 'company', 'location', 'description', 'extracted_skills', 
                              'job_category', 'seniority_level', 'is_remote', 'source', 'scraped_at',
                              'h1b_sponsor', 'h1b_employer_name', 'h1b_city', 'h1b_state', 
                              'total_petitions', 'avg_approval_rate', 
                              'description_embedding', 'skills_embedding'],
        on_schema_change='sync_all_columns'
    )
}}

WITH deduplicated_jobs AS (
    -- Use deduplicated jobs to prevent duplicates in EMBEDDED_JOBS
    SELECT * FROM {{ ref('dedup_jobs') }}
),

jobs AS (
    SELECT * FROM {{ ref('classified_jobs') }} c
    WHERE c.job_id IN (SELECT job_id FROM deduplicated_jobs)
    {% if is_incremental() %}
    -- Only process new jobs not already embedded (incremental optimization)
    AND c.job_id NOT IN (SELECT job_id FROM {{ this }})
    {% endif %}
),

embedded AS (
    SELECT
        job_id,
        title,
        company,
        location,
        description,
        extracted_skills,
        job_category,
        seniority_level,
        is_remote,
        source,
        scraped_at,
        h1b_sponsor,
        h1b_employer_name,
        h1b_city,
        h1b_state,
        total_petitions,
        avg_approval_rate,
        
        -- Generate embedding for job description
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            'e5-base-v2',
            CONCAT(
                title, '. ',
                company, '. ',
                LEFT(description, 2000)
            )
        ) AS description_embedding,
        
        -- Generate embedding for extracted skills
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            'e5-base-v2',
            COALESCE(extracted_skills, title)
        ) AS skills_embedding
        
    FROM jobs
)

SELECT * FROM embedded
