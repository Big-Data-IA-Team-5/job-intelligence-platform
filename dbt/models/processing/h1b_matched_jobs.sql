-- H1B Matched Jobs
-- Matches jobs with H1B sponsorship data from raw LCA records
{{
    config(
        materialized='table',
        schema='processing'
    )
}}

WITH jobs AS (
    SELECT * FROM {{ ref('dedup_jobs') }}
),

-- Aggregate H-1B data by employer
h1b_aggregated AS (
    SELECT 
        UPPER(TRIM(employer_name)) as employer_name_clean,
        employer_name as employer_name_original,
        COUNT(*) as total_petitions,
        SUM(CASE WHEN case_status = 'Certified' THEN 1 ELSE 0 END) as certified_petitions,
        AVG(CASE WHEN case_status = 'Certified' THEN 1.0 ELSE 0.0 END) as avg_approval_rate,
        MAX(worksite_city) as h1b_city,
        MAX(worksite_state) as h1b_state
    FROM {{ source('raw', 'h1b_raw') }}
    WHERE employer_name IS NOT NULL
    GROUP BY 1, 2
),

-- Match jobs to H-1B sponsors
matched AS (
    SELECT
        j.*,
        h.employer_name_original AS h1b_employer_name,
        h.h1b_city,
        h.h1b_state,
        h.total_petitions,
        h.avg_approval_rate,
        CASE 
            WHEN h.employer_name_clean IS NOT NULL THEN TRUE 
            ELSE FALSE 
        END AS h1b_sponsor
    FROM jobs j
    LEFT JOIN h1b_aggregated h
        ON UPPER(TRIM(j.company)) = h.employer_name_clean
        OR UPPER(TRIM(j.company)) LIKE h.employer_name_clean || '%'
        OR h.employer_name_clean LIKE UPPER(TRIM(j.company)) || '%'
)

SELECT * FROM matched