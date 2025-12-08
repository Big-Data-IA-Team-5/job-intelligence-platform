-- Embedded Jobs
-- Generates vector embeddings for semantic search
-- VECTOR types treated as VARIANT for dbt compatibility

{{
    config(
        materialized='table',
        unique_key='job_id',
        schema='processing',
        on_schema_change='sync_all_columns',
        full_refresh=true
    )
}}

WITH jobs AS (
    SELECT * FROM {{ ref('classified_jobs') }}
    {% if is_incremental() %}
    -- Only process new jobs
    WHERE scraped_at > (SELECT MAX(scraped_at) FROM {{ this }})
    {% endif %}
),

embedded AS (
    SELECT
        *,
        -- Generate embedding for job description (VECTOR type - do not cast)
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            'e5-base-v2',
            CONCAT(
                title, '. ',
                company, '. ',
                LEFT(description, 2000)
            )
        ) AS description_embedding,
        
        -- Generate embedding for extracted skills (VECTOR type - do not cast)
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            'e5-base-v2',
            COALESCE(extracted_skills, title)
        ) AS skills_embedding
        
    FROM jobs
)

SELECT * FROM embedded
