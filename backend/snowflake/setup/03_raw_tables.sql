-- ============================================
-- FILE 3: 03_raw_tables.sql - UPDATED
-- Raw Data Tables with Enhanced Schema
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE job_intelligence;
USE WAREHOUSE compute_wh;
USE SCHEMA raw;

-- ============================================
-- RAW TABLE 1: JOBS_RAW
-- Source: Web scrapers (Custom + JobSpy + Fortune500 + Airtable)
-- Owner: P1 (Data Engineering)
-- UPDATED: Added 7 new fields for enhanced job intelligence
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
    snippet STRING,
    
    -- Salary information
    salary_min NUMBER(10, 2),
    salary_max NUMBER(10, 2),
    salary_text STRING,
    
    -- Job classification
    job_type STRING,
    posted_date DATE,
    
    -- NEW ENHANCED FIELDS
    work_model VARCHAR(50),              -- Remote, Hybrid, Onsite
    department VARCHAR(100),             -- Engineering, Sales, etc.
    company_size VARCHAR(50),            -- Startup, Mid-size, Enterprise
    qualifications TEXT,                 -- Job requirements
    h1b_sponsored VARCHAR(10),           -- Yes, No, Unknown
    is_new_grad VARCHAR(10),             -- Yes, No
    category VARCHAR(100),               -- Job category
    
    -- Metadata
    scraped_at TIMESTAMP_NTZ NOT NULL,
    source STRING NOT NULL,
    raw_json VARIANT,
    
    COMMENT = 'Raw job postings - Enhanced schema with 22 fields'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs_raw(company);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped ON jobs_raw(scraped_at);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs_raw(location);
CREATE INDEX IF NOT EXISTS idx_jobs_work_model ON jobs_raw(work_model);
CREATE INDEX IF NOT EXISTS idx_jobs_h1b ON jobs_raw(h1b_sponsored);


-- ============================================
-- RAW TABLE 2: H1B_RAW
-- Source: USCIS FY2025 Q3 LCA Data
-- Owner: P1 (Data Engineering)
-- UPDATED: 90+ columns for comprehensive H-1B intelligence
-- ============================================

CREATE OR REPLACE TABLE h1b_raw (
    -- Primary identifier (matches FY2025 Q3 schema)
    case_number STRING PRIMARY KEY,
    
    -- Basic info
    case_status STRING,              -- CERTIFIED, DENIED, WITHDRAWN
    employer_name STRING NOT NULL,
    job_title STRING,
    soc_title STRING,
    
    -- Location (actual job location)
    worksite_city STRING,
    worksite_state STRING,
    
    -- Salary (CRITICAL for matching!)
    wage_rate_of_pay_from NUMBER(10,2),
    wage_rate_of_pay_to NUMBER(10,2),
    wage_unit_of_pay STRING,         -- Year, Hour, Week, Month
    
    -- Risk flags (NO underscore - matches upload code!)
    h1b_dependent STRING,            -- Y/N (high visa dependency)
    willful_violator STRING,         -- Y/N (immigration violations)
    
    -- Metadata
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'H-1B LCA Data FY2025 Q3 - Simplified schema matching upload_to_snowflake()'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_h1b_employer ON h1b_raw(employer_name);
CREATE INDEX IF NOT EXISTS idx_h1b_job_title ON h1b_raw(job_title);
CREATE INDEX IF NOT EXISTS idx_h1b_worksite ON h1b_raw(worksite_city, worksite_state);
CREATE INDEX IF NOT EXISTS idx_h1b_soc ON h1b_raw(soc_code);
CREATE INDEX IF NOT EXISTS idx_h1b_status ON h1b_raw(case_status);


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