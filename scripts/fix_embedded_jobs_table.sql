-- Fix embedded_jobs table VECTOR type issue
-- The problem: DBT 1.7.4 can't interpret VECTOR(FLOAT, 768) type
-- Solution: Drop and recreate with explicit column definitions

USE DATABASE JOB_INTELLIGENCE_DB;
USE SCHEMA PROCESSED_PROCESSING;

-- Drop existing table if it has the problematic VECTOR type
DROP TABLE IF EXISTS embedded_jobs;

-- Recreate with proper schema
-- Note: VARIANT works for storing vectors, and DBT can handle it
CREATE TABLE IF NOT EXISTS embedded_jobs (
    job_id VARCHAR(16777216),
    url VARCHAR(16777216),
    title VARCHAR(16777216),
    company VARCHAR(16777216),
    location VARCHAR(16777216),
    description VARCHAR(16777216),
    date_posted VARCHAR(16777216),
    employment_type VARCHAR(16777216),
    seniority_level VARCHAR(16777216),
    industries VARCHAR(16777216),
    job_functions VARCHAR(16777216),
    scraped_at TIMESTAMP_NTZ(9),
    source VARCHAR(16777216),
    application_url VARCHAR(16777216),
    company_url VARCHAR(16777216),
    category VARCHAR(16777216),
    is_duplicate BOOLEAN,
    duplicate_of VARCHAR(16777216),
    h1b_sponsor VARCHAR(16777216),
    h1b_job_title VARCHAR(16777216),
    h1b_wage_from NUMBER(38,0),
    h1b_wage_to NUMBER(38,0),
    h1b_match_type VARCHAR(16777216),
    h1b_confidence NUMBER(38,0),
    job_category VARCHAR(16777216),
    experience_level VARCHAR(16777216),
    remote_work VARCHAR(16777216),
    extracted_skills VARCHAR(16777216),
    required_education VARCHAR(16777216),
    classification_confidence NUMBER(38,2),
    description_embedding VARIANT,  -- Store VECTOR as VARIANT for DBT compatibility
    skills_embedding VARIANT        -- Store VECTOR as VARIANT for DBT compatibility
);

-- Verify table was created
SHOW TABLES LIKE 'embedded_jobs';
DESC TABLE embedded_jobs;
