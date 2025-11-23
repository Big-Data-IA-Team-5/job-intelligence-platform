-- Create processed tables schema
USE DATABASE JOB_INTELLIGENCE;
USE SCHEMA PROCESSING;
USE ROLE ACCOUNTADMIN;

-- Main processed jobs table (populated by DBT)
CREATE TABLE IF NOT EXISTS JOBS (
    job_id VARCHAR(255),
    source VARCHAR(50),
    title VARCHAR(500),
    company_name VARCHAR(500),
    location VARCHAR(500),
    description TEXT,
    posted_date TIMESTAMP_NTZ,
    salary_range VARCHAR(200),
    job_type VARCHAR(100),
    url TEXT,
    seniority_level VARCHAR(50),
    job_category VARCHAR(100),
    extracted_skills TEXT,
    is_remote BOOLEAN,
    likely_sponsors_h1b BOOLEAN,
    h1b_employer_name VARCHAR(500),
    h1b_job_title VARCHAR(500),
    h1b_application_count INTEGER,
    prevailing_wage NUMBER(12,2),
    description_embedding VECTOR(FLOAT, 768),
    skills_embedding VECTOR(FLOAT, 768),
    scraped_at TIMESTAMP_NTZ,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (job_id, source)
) COMMENT = 'Processed and enriched job postings';

-- Create stored procedure for running DBT pipeline
CREATE OR REPLACE PROCEDURE RUN_DBT_PIPELINE()
RETURNS STRING
LANGUAGE SQL
AS
$$
BEGIN
    -- This would typically call external DBT run
    -- For now, it's a placeholder that can be triggered by Airflow
    RETURN 'DBT pipeline triggered successfully';
END;
$$;

GRANT SELECT ON TABLE JOBS TO ROLE SYSADMIN;
GRANT USAGE ON PROCEDURE RUN_DBT_PIPELINE() TO ROLE SYSADMIN;
