-- ============================================
-- FILE 3: 03_raw_tables.sql
-- Raw Data Tables
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE job_intelligence;
USE WAREHOUSE compute_wh;
USE SCHEMA raw;

-- ============================================
-- RAW TABLE 1: JOBS_RAW
-- Source: Web scrapers (Custom Playwright + JobSpy)
-- Owner: P1 (Data Engineering)
-- ============================================

CREATE OR REPLACE TABLE jobs_raw (
    -- Primary identifiers
    job_id STRING PRIMARY KEY,
    url STRING UNIQUE NOT NULL,
    
    -- Basic job information
    title STRING NOT NULL,
    company STRING,
    location STRING,
    description TEXT,
    snippet STRING,                      -- Short description preview
    
    -- Salary information
    salary_min NUMBER(10, 2),
    salary_max NUMBER(10, 2),
    salary_text STRING,                  -- Original salary text
    
    -- Job classification
    job_type STRING,                     -- Internship, Full-time, Remote, etc.
    posted_date DATE,
    
    -- Metadata
    scraped_at TIMESTAMP_NTZ NOT NULL,
    source STRING NOT NULL,              -- indeed_custom, indeed_jobspy
    raw_json VARIANT,                    -- Full original JSON
    
    COMMENT = 'Raw job postings from web scrapers - loaded by Airflow'
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs_raw(company);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs_raw(scraped_at);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs_raw(location);


-- ============================================
-- RAW TABLE 2: H1B_RAW
-- Source: Bloomberg H-1B Dataset (GitHub)
-- Owner: P1 (Data Engineering)
-- ============================================

CREATE OR REPLACE TABLE h1b_raw (
    -- Employer information
    employer_name STRING NOT NULL,
    employer_city STRING,
    employer_state STRING,
    
    -- Fiscal year and petition data
    fiscal_year NUMBER NOT NULL,
    total_petitions NUMBER,
    initial_approval NUMBER,
    initial_denial NUMBER,
    continuing_approval NUMBER,
    continuing_denial NUMBER,
    approval_rate FLOAT,
    
    -- Additional metadata
    naics_code STRING,                   -- Industry classification
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'H-1B sponsorship data from Bloomberg/USCIS - 500K+ records'
);

-- Create index for company matching
CREATE INDEX IF NOT EXISTS idx_h1b_employer ON h1b_raw(employer_name);


-- ============================================
-- RAW TABLE 3: RESUMES_RAW
-- Source: User uploads via API
-- Owner: P3 (Frontend)
-- ============================================

CREATE OR REPLACE TABLE resumes_raw (
    -- Primary identifier
    resume_id STRING PRIMARY KEY,
    
    -- User information
    user_id STRING,                      -- Links to user_profiles
    
    -- File information
    file_name STRING NOT NULL,
    file_size_bytes NUMBER,
    
    -- Extracted text
    raw_text TEXT NOT NULL,              -- Extracted from PDF
    
    -- Metadata
    uploaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'User-uploaded resumes (PDF text extraction)'
);

-- Create index for user lookups
CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes_raw(user_id);


-- ============================================
-- VERIFY RAW TABLES
-- ============================================

SHOW TABLES IN SCHEMA raw;

SELECT 
    COUNT(*) as total_tables,
    'Raw tables created successfully!' as status
FROM INFORMATION_SCHEMA.TABLES
WHERE table_schema = 'RAW';

