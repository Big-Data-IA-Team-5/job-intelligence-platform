-- Staging: Initial view of raw jobs data
-- Performs basic cleaning and type casting
{{
    config(
        materialized='view',
        schema='staging'
    )
}}

SELECT
    job_id,
    source,
    TRIM(title) AS title,
    TRIM(company) AS company,
    TRIM(location) AS location,
    description,
    snippet,
    posted_date,
    salary_min,
    salary_max,
    salary_text,
    job_type,
    url,
    scraped_at,
    CURRENT_TIMESTAMP() AS processed_at
FROM {{ source('raw', 'jobs_raw') }}
WHERE 
    job_id IS NOT NULL
    AND title IS NOT NULL
    AND company IS NOT NULL
    -- Only get recent jobs (last 90 days)
    AND scraped_at >= DATEADD(day, -90, CURRENT_DATE())