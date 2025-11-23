-- ============================================
-- FILE 4: 04_processed_tables.sql
-- Processed Tables with AI Features
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE job_intelligence;
USE WAREHOUSE compute_wh;
USE SCHEMA processed;

-- ============================================
-- PROCESSED TABLE 1: JOBS_PROCESSED
-- Source: dbt transformations + AI agents
-- Owner: P1 (dbt) + P2 (Agent 3 classification)
-- ============================================

CREATE OR REPLACE TABLE jobs_processed (
    -- Primary identifiers
    job_id STRING PRIMARY KEY,
    url STRING UNIQUE NOT NULL,
    
    -- Basic information (cleaned)
    title STRING NOT NULL,
    company_clean STRING,                -- Standardized company name
    location STRING,
    location_city STRING,                -- Parsed city
    location_state STRING,               -- Parsed state
    description TEXT,
    
    -- Salary
    salary_min NUMBER(10, 2),
    salary_max NUMBER(10, 2),
    job_type STRING,
    
    -- Time-based
    posted_date DATE,
    days_since_posted NUMBER,            -- Calculated: CURRENT_DATE - posted_date
    
    -- H-1B MATCHING (from Bloomberg dataset)
    h1b_sponsor BOOLEAN DEFAULT FALSE,
    h1b_approval_rate FLOAT,
    h1b_total_petitions NUMBER,
    h1b_match_confidence FLOAT,          -- Matching confidence (0-1)
    
    -- VISA CLASSIFICATION (Agent 3 output)
    visa_category STRING,                -- CPT, OPT, H-1B, US-Only
    classification_confidence FLOAT,     -- Agent 3 confidence (0-1)
    classification_signals ARRAY,        -- Keywords found ['cpt', 'intern']
    classified_at TIMESTAMP_NTZ,
    
    -- VECTOR EMBEDDING (Cortex)
    job_embedding VECTOR(FLOAT, 768),    -- For semantic search
    
    -- Metadata
    source STRING,                       -- Original source
    scraped_at TIMESTAMP_NTZ,
    processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'Processed jobs with AI classifications and embeddings'
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_processed_visa ON jobs_processed(visa_category);
CREATE INDEX IF NOT EXISTS idx_processed_company ON jobs_processed(company_clean);
CREATE INDEX IF NOT EXISTS idx_processed_location ON jobs_processed(location_city, location_state);


-- ============================================
-- PROCESSED TABLE 2: RESUME_PROFILES
-- Source: Agent 4 extraction
-- Owner: P2 (Agent 4)
-- ============================================

CREATE OR REPLACE TABLE resume_profiles (
    -- Primary identifier
    resume_id STRING PRIMARY KEY,
    user_id STRING,
    
    -- EXTRACTED INFORMATION (Agent 4 output)
    technical_skills ARRAY,              -- ['Python', 'SQL', 'React']
    soft_skills ARRAY,                   -- ['Leadership', 'Communication']
    total_experience_years FLOAT,        -- 3.5 years
    education_level STRING,              -- Bachelor's, Master's, PhD
    work_authorization STRING,           -- F-1 CPT, F-1 OPT, H-1B, etc.
    
    -- JOB PREFERENCES (Agent 4 extraction)
    desired_roles ARRAY,                 -- ['Data Engineer', 'ML Engineer']
    preferred_locations ARRAY,           -- ['Boston', 'Remote']
    salary_min NUMBER,                   -- Minimum expected salary
    
    -- VECTOR EMBEDDING (Cortex)
    resume_embedding VECTOR(FLOAT, 768), -- For semantic matching
    
    -- Raw data
    raw_text TEXT,                       -- Full resume text
    
    -- Metadata
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'Extracted resume profiles with AI-generated embeddings'
);


-- ============================================
-- PROCESSED TABLE 3: JOB_MATCHES
-- Source: Agent 4 matching algorithm
-- Owner: P2 (Agent 4)
-- ============================================

CREATE OR REPLACE TABLE job_matches (
    -- Primary identifier
    match_id STRING PRIMARY KEY,
    
    -- Foreign keys
    resume_id STRING NOT NULL,
    job_id STRING NOT NULL,
    
    -- MATCH SCORES (0-100)
    overall_score NUMBER(5, 2),          -- Overall match score
    skills_score NUMBER(5, 2),           -- Technical skills alignment
    experience_score NUMBER(5, 2),       -- Experience level fit
    visa_score NUMBER(5, 2),             -- Visa compatibility
    location_score NUMBER(5, 2),         -- Location preference match
    growth_score NUMBER(5, 2),           -- Career growth potential
    
    -- AI REASONING
    match_reasoning STRING,              -- Explanation (max 200 chars)
    
    -- Metadata
    matched_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'Resume-to-job matches with AI-generated scores and reasoning'
);

-- Indexes for lookups
CREATE INDEX IF NOT EXISTS idx_matches_resume ON job_matches(resume_id);
CREATE INDEX IF NOT EXISTS idx_matches_job ON job_matches(job_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON job_matches(overall_score DESC);


-- ============================================
-- PROCESSED TABLE 4: H1B_SPONSORS
-- Source: dbt transformation of h1b_raw
-- Owner: P1 (dbt)
-- ============================================

CREATE OR REPLACE TABLE h1b_sponsors (
    -- Primary identifier
    employer_name STRING PRIMARY KEY,
    employer_clean STRING,               -- Standardized name (UPPER, trimmed)
    
    -- Petition statistics
    total_petitions NUMBER,
    approval_rate FLOAT,                 -- 0-1
    fiscal_year NUMBER,
    
    -- Location
    employer_city STRING,
    employer_state STRING,
    
    -- Metadata
    last_updated TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'H-1B sponsor companies - deduplicated and standardized'
);


-- ============================================
-- PROCESSED TABLE 5: CLASSIFICATION_CACHE
-- Source: Agent 3 classifications
-- Owner: P2 (Agent 3)
-- Purpose: Reduce LLM costs by caching results
-- ============================================

CREATE OR REPLACE TABLE classification_cache (
    -- Primary identifier
    job_url STRING PRIMARY KEY,
    
    -- Cached classification
    classification_json VARIANT,         -- Full Agent 3 response
    confidence FLOAT,
    
    -- Cache management
    cached_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    ttl TIMESTAMP_NTZ,                   -- Time to live (7 days default)
    
    COMMENT = 'Cached LLM classifications to optimize costs (10% hit rate expected)'
);


-- ============================================
-- VERIFY ALL PROCESSED TABLES
-- ============================================

SHOW TABLES IN SCHEMA processed;

SELECT 
    COUNT(*) as total_tables,
    'All processed tables created successfully!' as status
FROM INFORMATION_SCHEMA.TABLES
WHERE table_schema = 'PROCESSED';
