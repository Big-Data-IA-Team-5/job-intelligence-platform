-- H1B Matched Jobs
-- Matches jobs with H1B sponsorship data

{{
    config(
        materialized='table',
        schema='processing'
    )
}}

WITH jobs AS (
    SELECT * FROM {{ ref('dedup_jobs') }}
),

h1b_data AS (
    SELECT DISTINCT
        employer_name,
        job_title,
        worksite_city,
        worksite_state,
        prevailing_wage,
        COUNT(*) as h1b_application_count
    FROM {{ source('raw', 'h1b_data') }}
    WHERE 
        case_status = 'Certified'
        AND fiscal_year >= YEAR(CURRENT_DATE()) - 3
    GROUP BY 1, 2, 3, 4, 5
),

matched AS (
    SELECT
        j.*,
        h.employer_name AS h1b_employer_name,
        h.job_title AS h1b_job_title,
        h.prevailing_wage,
        h.h1b_application_count,
        CASE 
            WHEN h.employer_name IS NOT NULL THEN TRUE 
            ELSE FALSE 
        END AS likely_sponsors_h1b
    FROM jobs j
    LEFT JOIN h1b_data h
        ON LOWER(j.company_name) LIKE LOWER('%' || h.employer_name || '%')
        AND LOWER(j.title) LIKE LOWER('%' || SPLIT_PART(h.job_title, ' ', 1) || '%')
)

SELECT * FROM matched
