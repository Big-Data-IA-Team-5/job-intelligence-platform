-- Embedded Jobs
-- Generates vector embeddings for semantic search
-- VECTOR types treated as VARIANT for dbt compatibility

{{
    config(
        materialized='incremental',
        unique_key='job_id',
        schema='processing',
        on_schema_change='sync_all_columns',
        merge_update_columns=['title', 'company', 'location', 'description', 'scraped_at']
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
    -- Only process new jobs not already embedded
    AND c.job_id NOT IN (SELECT job_id FROM {{ this }})
    {% endif %}
),

embedded AS (
    SELECT
        *,
        -- Generate embedding for job description (cast to VARIANT for dbt compatibility)
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            'e5-base-v2',
            CONCAT(
                title, '. ',
                company, '. ',
                LEFT(description, 2000)
            )
        )::VARIANT AS description_embedding,
        
        -- Generate embedding for extracted skills (cast to VARIANT for dbt compatibility)
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            'e5-base-v2',
            COALESCE(extracted_skills, title)
        )::VARIANT AS skills_embedding
        
    FROM jobs
)

SELECT * FROM embedded
