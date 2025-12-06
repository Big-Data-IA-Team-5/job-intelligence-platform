-- Embedded Jobs
-- Generates vector embeddings for semantic search
-- VECTOR types cast to VARIANT for dbt compatibility

{{
    config(
        materialized='incremental',
        unique_key='job_id',
        schema='processing',
        on_schema_change='ignore'
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
        -- Generate embedding for job description (cast to VARIANT for dbt compatibility)
        TO_VARIANT(
            SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                'e5-base-v2',
                CONCAT(
                    title, '. ',
                    company, '. ',
                    LEFT(description, 2000)
                )
            )
        ) AS description_embedding,
        
        -- Generate embedding for extracted skills (cast to VARIANT for dbt compatibility)
        TO_VARIANT(
            SNOWFLAKE.CORTEX.EMBED_TEXT_768(
                'e5-base-v2',
                COALESCE(extracted_skills, title)
            )
        ) AS skills_embedding
        
    FROM jobs
)

SELECT * FROM embedded
