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
        -- Calculate REAL approval rate: certified / total filings
        (SUM(CASE WHEN case_status = 'Certified' THEN 1 ELSE 0 END) * 1.0 / COUNT(*)) as avg_approval_rate,
        MAX(worksite_city) as h1b_city,
        MAX(worksite_state) as h1b_state
    FROM {{ source('raw', 'h1b_raw') }}
    WHERE employer_name IS NOT NULL
    GROUP BY 1, 2
),

-- Match jobs to H-1B sponsors with deduplication
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
        END AS h1b_sponsor,
        -- Priority: exact match > company contains h1b > h1b contains company
        CASE
            WHEN UPPER(TRIM(j.company)) = h.employer_name_clean THEN 1
            WHEN UPPER(TRIM(j.company)) LIKE h.employer_name_clean || '%' THEN 2
            WHEN h.employer_name_clean LIKE UPPER(TRIM(j.company)) || '%' THEN 3
            ELSE 4
        END AS match_priority
    FROM jobs j
    LEFT JOIN h1b_aggregated h
        ON UPPER(TRIM(j.company)) = h.employer_name_clean
        OR UPPER(TRIM(j.company)) LIKE h.employer_name_clean || '%'
        OR h.employer_name_clean LIKE UPPER(TRIM(j.company)) || '%'
    QUALIFY ROW_NUMBER() OVER (PARTITION BY j.job_id ORDER BY match_priority, h.total_petitions DESC) = 1
)

SELECT 
    job_id, title, company, location, description, source, scraped_at,
    h1b_employer_name, h1b_city, h1b_state, total_petitions, avg_approval_rate, h1b_sponsor
FROM matched