-- ============================================================================
-- FIX DUPLICATES AND OPTIMIZE DATABASE
-- ============================================================================
-- This script:
-- 1. Backs up current data
-- 2. Removes 25,769 duplicate jobs from JOBS_PROCESSED
-- 3. Removes 1,093 duplicates from JOBS_RAW
-- 4. Adds unique constraints
-- ============================================================================

USE DATABASE job_intelligence;
USE SCHEMA PROCESSED;

-- ============================================================================
-- STEP 1: BACKUP EXISTING DATA
-- ============================================================================
CREATE OR REPLACE TABLE JOBS_PROCESSED_BEFORE_DEDUP AS 
SELECT * FROM JOBS_PROCESSED;

SELECT 
    COUNT(*) as total_before_dedup,
    COUNT(DISTINCT JOB_ID) as unique_jobs
FROM JOBS_PROCESSED_BEFORE_DEDUP;

-- ============================================================================
-- STEP 2: CREATE CLEAN DEDUPLICATED TABLE
-- ============================================================================
-- Keep only the most recent version of each job
CREATE OR REPLACE TABLE JOBS_PROCESSED_CLEAN AS
WITH ranked_jobs AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY JOB_ID 
            ORDER BY 
                SCRAPED_AT DESC,
                PROCESSED_AT DESC
        ) as rn
    FROM JOBS_PROCESSED
)
SELECT 
    JOB_ID,
    SOURCE,
    URL,
    TITLE,
    COMPANY,
    LOCATION,
    DESCRIPTION,
    SNIPPET,
    JOB_TYPE,
    POSTED_DATE,
    SCRAPED_AT,
    SALARY_MIN,
    SALARY_MAX,
    SALARY_TEXT,
    H1B_SPONSOR,
    H1B_EMPLOYER_NAME,
    H1B_CITY,
    H1B_STATE,
    TOTAL_PETITIONS,
    AVG_APPROVAL_RATE,
    DESCRIPTION_EMBEDDING,
    PROCESSED_AT,
    COMPANY_CLEAN,
    VISA_CATEGORY,
    QUALIFICATIONS,
    DAYS_SINCE_POSTED,
    CLASSIFICATION_CONFIDENCE,
    WORK_MODEL,
    DEPARTMENT,
    COMPANY_SIZE,
    H1B_SPONSORED_EXPLICIT,
    IS_NEW_GRAD_ROLE,
    JOB_CATEGORY,
    H1B_APPROVAL_RATE,
    H1B_TOTAL_PETITIONS,
    SPONSORSHIP_SCORE,
    H1B_RISK_LEVEL,
    H1B_AVG_WAGE
FROM ranked_jobs
WHERE rn = 1;

-- Verify deduplication
SELECT 
    COUNT(*) as total_after_dedup,
    COUNT(DISTINCT JOB_ID) as unique_jobs,
    COUNT(*) - COUNT(DISTINCT JOB_ID) as remaining_duplicates
FROM JOBS_PROCESSED_CLEAN;

-- ============================================================================
-- STEP 3: REPLACE OLD TABLE WITH CLEAN VERSION
-- ============================================================================
ALTER TABLE JOBS_PROCESSED RENAME TO JOBS_PROCESSED_OLD_WITH_DUPS;
ALTER TABLE JOBS_PROCESSED_CLEAN RENAME TO JOBS_PROCESSED;

-- ============================================================================
-- STEP 4: FIX JOBS_RAW DUPLICATES
-- ============================================================================
USE SCHEMA RAW;

CREATE OR REPLACE TABLE JOBS_RAW_CLEAN AS
WITH ranked_jobs AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY JOB_ID 
            ORDER BY SCRAPED_AT DESC
        ) as rn
    FROM JOBS_RAW
    WHERE JOB_ID IS NOT NULL AND JOB_ID != 'N/A'
)
SELECT 
    JOB_ID,
    URL,
    TITLE,
    COMPANY,
    LOCATION,
    DESCRIPTION,
    SNIPPET,
    SALARY_MIN,
    SALARY_MAX,
    SALARY_TEXT,
    JOB_TYPE,
    POSTED_DATE,
    SCRAPED_AT,
    SOURCE,
    RAW_JSON,
    WORK_MODEL,
    DEPARTMENT,
    COMPANY_SIZE,
    QUALIFICATIONS,
    H1B_SPONSORED,
    IS_NEW_GRAD,
    CATEGORY,
    RN
FROM ranked_jobs
WHERE rn = 1;

-- Verify
SELECT 
    COUNT(*) as total,
    COUNT(DISTINCT JOB_ID) as unique_jobs
FROM JOBS_RAW_CLEAN;

-- Replace
ALTER TABLE JOBS_RAW RENAME TO JOBS_RAW_OLD_WITH_DUPS;
ALTER TABLE JOBS_RAW_CLEAN RENAME TO JOBS_RAW;

-- ============================================================================
-- STEP 5: ADD UNIQUE CONSTRAINTS (if supported by Snowflake version)
-- ============================================================================
-- Note: Snowflake doesn't enforce UNIQUE constraints, but we can add them for documentation
-- ALTER TABLE PROCESSED.JOBS_PROCESSED ADD CONSTRAINT uk_job_id UNIQUE (JOB_ID);
-- ALTER TABLE RAW.JOBS_RAW ADD CONSTRAINT uk_job_id_raw UNIQUE (JOB_ID);

-- ============================================================================
-- STEP 6: VERIFICATION REPORT
-- ============================================================================
SELECT '=== DEDUPLICATION COMPLETE ===' as status;

SELECT 
    'JOBS_PROCESSED' as table_name,
    COUNT(*) as final_count,
    COUNT(DISTINCT JOB_ID) as unique_jobs,
    COUNT(*) - COUNT(DISTINCT JOB_ID) as duplicates_remaining
FROM PROCESSED.JOBS_PROCESSED

UNION ALL

SELECT 
    'JOBS_RAW' as table_name,
    COUNT(*) as final_count,
    COUNT(DISTINCT JOB_ID) as unique_jobs,
    COUNT(*) - COUNT(DISTINCT JOB_ID) as duplicates_remaining
FROM RAW.JOBS_RAW;

-- ============================================================================
-- CLEANUP OLD BACKUP TABLES (optional - uncomment after verification)
-- ============================================================================
-- DROP TABLE IF EXISTS PROCESSED.JOBS_PROCESSED_OLD_WITH_DUPS;
-- DROP TABLE IF EXISTS RAW.JOBS_RAW_OLD_WITH_DUPS;
-- DROP TABLE IF EXISTS PROCESSED.JOBS_PROCESSED_BEFORE_DEDUP;
