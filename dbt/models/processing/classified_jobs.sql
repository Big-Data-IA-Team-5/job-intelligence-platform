{{ config(
    materialized='incremental',
    unique_key='job_id',
    tags=['classification', 'agent3']
) }}

/*
Classify jobs using Agent 3 (Visa Classifier)
Calls Mixtral 8x7B to determine: CPT, OPT, H-1B, or US-Only
*/

WITH unclassified_jobs AS (
    SELECT 
        job_id,
        url,
        title,
        company_clean,
        location,
        description
    FROM {{ ref('h1b_matched_jobs') }}
    
    {% if is_incremental() %}
    -- Only process new jobs in incremental mode
    WHERE processed_at > (SELECT MAX(classified_at) FROM {{ this }})
    {% endif %}
),

-- Call Agent 3 for classification (simplified for dbt)
-- In production, this would call the Python agent
-- For now, use keyword-based classification
classifications AS (
    SELECT
        job_id,
        url,
        title,
        company_clean,
        location,
        description,
        
        -- Simple classification logic (will be replaced by Agent 3)
        CASE
            WHEN LOWER(title) LIKE '%intern%' OR LOWER(description) LIKE '%cpt%' THEN 'CPT'
            WHEN LOWER(description) LIKE '%opt%' OR LOWER(description) LIKE '%new grad%' THEN 'OPT'
            WHEN LOWER(description) LIKE '%sponsor%' OR LOWER(description) LIKE '%h-1b%' THEN 'H-1B'
            WHEN LOWER(description) LIKE '%citizenship%' OR LOWER(description) LIKE '%clearance%' THEN 'US-Only'
            ELSE 'Unknown'
        END as visa_category,
        
        -- Confidence (placeholder - Agent 3 provides real confidence)
        CASE
            WHEN LOWER(description) LIKE '%cpt eligible%' THEN 0.95
            WHEN LOWER(description) LIKE '%sponsor h-1b%' THEN 0.90
            WHEN LOWER(description) LIKE '%citizenship required%' THEN 0.95
            ELSE 0.70
        END as classification_confidence,
        
        -- Signals found
        ARRAY_CONSTRUCT(
            CASE WHEN LOWER(title) LIKE '%intern%' THEN 'intern' END,
            CASE WHEN LOWER(description) LIKE '%cpt%' THEN 'cpt' END,
            CASE WHEN LOWER(description) LIKE '%sponsor%' THEN 'sponsor' END
        ) as classification_signals,
        
        CURRENT_TIMESTAMP() as classified_at
        
    FROM unclassified_jobs
)

SELECT * FROM classifications
WHERE visa_category != 'Unknown'