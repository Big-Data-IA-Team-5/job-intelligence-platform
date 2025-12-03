-- Deduplicated jobs view
-- Keeps the most recent scrape of each job
{{
    config(
        materialized='view',
        schema='staging'
    )
}}

WITH ranked_jobs AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY job_id, source 
            ORDER BY scraped_at DESC
        ) AS rn
    FROM {{ ref('stg_jobs') }}
)

SELECT
    job_id,
    source,
    title,
    company,
    location,
    description,
    snippet,
    posted_date,
    salary_min,
    salary_max,
    salary_text,
    job_type,
    url,
    scraped_at,
    processed_at
FROM ranked_jobs
WHERE rn = 1