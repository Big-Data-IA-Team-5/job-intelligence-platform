-- Fix EMPLOYER_INTELLIGENCE approval rate calculation
-- Current: approval_rate = Certified / (Certified + Denied) -- excludes Withdrawn
-- Fixed: approval_rate = Certified / Total Filings -- includes all statuses

CREATE OR REPLACE VIEW EMPLOYER_INTELLIGENCE AS
WITH employer_metrics AS (
    SELECT 
        UPPER(TRIM(employer_name)) as employer_clean,
        employer_name as employer_original,
        
        -- Petition counts
        COUNT(*) as total_filings,
        COUNT_IF(case_status = 'Certified') as total_certified,
        COUNT_IF(case_status = 'Denied') as total_denied,
        
        -- FIXED: Approval rate = Certified / All Filings (includes Withdrawn)
        -- This gives the REAL approval rate that matters to applicants
        DIV0(COUNT_IF(case_status = 'Certified'), COUNT(*)) as approval_rate,
        
        -- Recent activity (last 6 months)
        COUNT_IF(loaded_at >= DATEADD(month, -6, CURRENT_DATE())) as filings_6mo,
        
        -- Salary data (convert hourly to annual)
        AVG(
            CASE 
                WHEN wage_unit_of_pay = 'Hour' THEN wage_rate_of_pay_from * 2080
                WHEN wage_unit_of_pay = 'Year' THEN wage_rate_of_pay_from
                ELSE wage_rate_of_pay_from
            END
        ) as avg_wage_offered,
        
        -- Risk flag
        MAX(CASE WHEN willful_violator = 'Y' THEN TRUE ELSE FALSE END) as is_violator,
        
        -- Location diversity
        COUNT(DISTINCT worksite_state) as states_count,
        
        MAX(loaded_at) as last_filing_date
        
    FROM raw.h1b_raw
    WHERE case_status IN ('Certified', 'Denied', 'Withdrawn')
    GROUP BY 1, 2
)

SELECT 
    *,
    -- SPONSORSHIP SCORE (0-100)
    ROUND(
        (approval_rate * 35) +                          -- 35% weight: approval rate
        (LEAST(filings_6mo / 10.0, 1.0) * 25) +       -- 25% weight: recent activity
        (LEAST(total_filings / 100.0, 1.0) * 15) +    -- 15% weight: experience
        (CASE WHEN is_violator THEN 0 ELSE 20 END) +  -- 20% weight: compliance
        (LEAST(states_count / 10.0, 1.0) * 5),        -- 5% weight: geographic diversity
    1) as sponsorship_score,
    
    -- Risk level
    CASE 
        WHEN is_violator THEN 'High Risk'
        WHEN approval_rate < 0.5 THEN 'High Risk'
        WHEN approval_rate < 0.75 THEN 'Medium Risk'
        ELSE 'Low Risk'
    END as risk_level
    
FROM employer_metrics
WHERE total_filings >= 5;

-- Verify the fix
SELECT 
    employer_original,
    total_filings,
    total_certified,
    total_denied,
    approval_rate,
    ROUND(approval_rate * 100, 2) as approval_percentage
FROM employer_intelligence
WHERE employer_original ILIKE '%amazon.com services%'
LIMIT 5;
