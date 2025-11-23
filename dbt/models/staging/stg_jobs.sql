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
    TRIM(company_name) AS company_name,
    TRIM(location) AS location,
    description,
    posted_date,
    salary_range,
    job_type,
    url,
    scraped_at,
    CURRENT_TIMESTAMP() AS processed_at
FROM {{ source('raw', 'jobs') }}
WHERE 
    job_id IS NOT NULL
    AND title IS NOT NULL
    AND company_name IS NOT NULL
    -- Filter out jobs older than configured days
    AND posted_date >= DATEADD(day, -{{ var('max_job_age_days', 90) }}, CURRENT_DATE())
