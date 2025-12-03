-- Classified Jobs
-- Uses Snowflake Cortex to classify jobs by category, seniority, etc.

{{
    config(
        materialized='table',
        schema='processing'
    )
}}

WITH jobs AS (
    SELECT * FROM {{ ref('h1b_matched_jobs') }}
),

classified AS (
    SELECT
        *,
        -- Use Cortex Complete for classification
        SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large',
            CONCAT(
                'Classify this job into one category: Engineering, Data, Product, Design, Sales, Marketing, Operations, Other. ',
                'Job title: ', title, '. ',
                'Description: ', LEFT(description, 500), '. ',
                'Return only the category name.'
            )
        ) AS job_category,
        
        -- Seniority level detection
        CASE
            WHEN LOWER(title) LIKE '%senior%' OR LOWER(title) LIKE '%sr %' OR LOWER(title) LIKE '%lead%' THEN 'Senior'
            WHEN LOWER(title) LIKE '%junior%' OR LOWER(title) LIKE '%jr %' OR LOWER(title) LIKE '%entry%' THEN 'Junior'
            WHEN LOWER(title) LIKE '%principal%' OR LOWER(title) LIKE '%staff%' THEN 'Principal'
            WHEN LOWER(title) LIKE '%manager%' OR LOWER(title) LIKE '%director%' THEN 'Management'
            ELSE 'Mid-Level'
        END AS seniority_level,
        
        -- Remote work detection
        CASE
            WHEN LOWER(location) LIKE '%remote%' THEN TRUE
            WHEN LOWER(description) LIKE '%remote%' OR LOWER(description) LIKE '%work from home%' THEN TRUE
            ELSE FALSE
        END AS is_remote,
        
        -- Extract skills using Cortex
        SNOWFLAKE.CORTEX.COMPLETE(
            'mistral-large',
            CONCAT(
                'Extract the top 5 technical skills mentioned in this job description. ',
                'Return as comma-separated list. Description: ',
                LEFT(description, 1000)
            )
        ) AS extracted_skills
        
    FROM jobs
)

SELECT * FROM classified
