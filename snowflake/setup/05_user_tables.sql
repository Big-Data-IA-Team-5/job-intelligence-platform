-- ============================================
-- FILE 5: 05_user_tables.sql
-- User-Facing Tables and Permissions
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE job_intelligence;
USE WAREHOUSE compute_wh;
USE SCHEMA users;

-- ============================================
-- USER TABLE 1: USER_PROFILES
-- Source: User registration
-- Owner: P3 (API)
-- ============================================

CREATE OR REPLACE TABLE user_profiles (
    -- Primary identifier
    user_id STRING PRIMARY KEY,
    
    -- User information
    email STRING UNIQUE,
    name STRING,
    
    -- Current status
    current_visa_status STRING,          -- F-1, OPT, H-1B, Citizen
    
    -- Preferences
    preferred_locations ARRAY,           -- ['Boston', 'New York', 'Remote']
    target_salary_min NUMBER,
    target_job_types ARRAY,              -- ['Internship', 'Full-time']
    
    -- Metadata
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    last_login TIMESTAMP_NTZ,
    
    COMMENT = 'User profiles and preferences'
);


-- ============================================
-- USER TABLE 2: USER_SAVED_JOBS
-- Source: User actions in UI
-- Owner: P3 (API)
-- ============================================

CREATE OR REPLACE TABLE user_saved_jobs (
    -- Primary identifier
    save_id STRING PRIMARY KEY,
    
    -- Foreign keys
    user_id STRING NOT NULL,
    job_url STRING NOT NULL,
    
    -- Tracking
    saved_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    notes TEXT,                          -- User's personal notes
    status STRING DEFAULT 'saved',       -- saved, applied, interviewing, offer, rejected
    status_updated_at TIMESTAMP_NTZ,
    
    COMMENT = 'User-saved jobs with application tracking'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_saved_user ON user_saved_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_status ON user_saved_jobs(status);


-- ============================================
-- USER TABLE 3: JOB_ALERTS
-- Source: User preferences in UI
-- Owner: P3 (API)
-- ============================================

CREATE OR REPLACE TABLE job_alerts (
    -- Primary identifier
    alert_id STRING PRIMARY KEY,
    
    -- Foreign key
    user_id STRING NOT NULL,
    
    -- Alert configuration
    keywords ARRAY,                      -- ['data engineer', 'python']
    location STRING,
    visa_filter ARRAY,                   -- ['CPT', 'OPT']
    salary_min NUMBER,
    job_type STRING,
    
    -- Frequency
    frequency STRING,                    -- realtime, daily, weekly
    last_sent TIMESTAMP_NTZ,
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    
    COMMENT = 'User job alert configurations'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_alerts_user ON job_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON job_alerts(active);


-- ============================================
-- USER TABLE 4: APPLICATION_HISTORY
-- Source: User actions tracking
-- Owner: P3 (API)
-- ============================================

CREATE OR REPLACE TABLE application_history (
    -- Primary identifier
    history_id STRING PRIMARY KEY,
    
    -- Foreign keys
    user_id STRING NOT NULL,
    job_url STRING NOT NULL,
    
    -- Application details
    applied_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    application_method STRING,           -- direct, referral, linkedin
    
    -- Status tracking
    current_status STRING,               -- applied, screening, interview, offer, rejected
    status_history ARRAY,                -- [{"status": "applied", "date": "..."}]
    
    -- Interview details
    interview_dates ARRAY,
    interview_notes TEXT,
    
    -- Offer details
    offer_amount NUMBER,
    offer_date DATE,
    
    -- Final outcome
    accepted BOOLEAN,
    rejection_reason STRING,
    
    COMMENT = 'Complete application and interview tracking history'
);


-- ============================================
-- VERIFY USER TABLES
-- ============================================

SHOW TABLES IN SCHEMA users;

SELECT 
    COUNT(*) as total_tables,
    'All user tables created successfully!' as status
FROM INFORMATION_SCHEMA.TABLES
WHERE table_schema = 'USERS';


-- ============================================
-- COMPLETE VERIFICATION - ALL FILES
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE job_intelligence;

-- Summary of all tables
SELECT 
    table_schema,
    COUNT(*) as table_count
FROM INFORMATION_SCHEMA.TABLES
WHERE table_catalog = 'JOB_INTELLIGENCE'
    AND table_schema IN ('RAW', 'STAGING', 'PROCESSED', 'ANALYTICS', 'USERS')
GROUP BY table_schema
ORDER BY table_schema;

-- Expected:
-- RAW: 3 tables
-- PROCESSED: 5 tables
-- USERS: 4 tables
-- Total: 12 tables

SELECT '✅ ALL SNOWFLAKE TABLES CREATED SUCCESSFULLY!' as final_status;
