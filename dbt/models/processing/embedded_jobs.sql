-- Embedded Jobs
-- Generates vector embeddings for semantic search

{{
    config(
        materialized='incremental',
        unique_key='job_id',
        schema='processing'
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
        -- Generate embedding for job description
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            '{{ var("embedding_model") }}',
            CONCAT(
                title, '. ',
                company_name, '. ',
                LEFT(description, 2000)
            )
        ) AS description_embedding,
        
        -- Generate embedding for extracted skills
        SNOWFLAKE.CORTEX.EMBED_TEXT_768(
            '{{ var("embedding_model") }}',
            COALESCE(extracted_skills, title)
        ) AS skills_embedding
        
    FROM jobs
)

SELECT * FROM embedded
