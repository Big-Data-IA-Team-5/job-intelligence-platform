- ============================================
-- FILE 2: 02_schemas.sql
-- Schema Creation (Data Organization)
-- ============================================

USE ROLE ACCOUNTADMIN;
USE DATABASE job_intelligence;

-- Schema 1: RAW - Unprocessed data from external sources
CREATE SCHEMA IF NOT EXISTS raw
    COMMENT = 'Raw data from scrapers, APIs, and file uploads';

-- Schema 2: STAGING - Intermediate transformations (dbt)
CREATE SCHEMA IF NOT EXISTS staging
    COMMENT = 'Staging area for dbt transformations';

-- Schema 3: PROCESSED - Clean, transformed data
CREATE SCHEMA IF NOT EXISTS processed
    COMMENT = 'Processed data ready for analytics and agents';

-- Schema 4: ANALYTICS - Business intelligence tables
CREATE SCHEMA IF NOT EXISTS analytics
    COMMENT = 'Analytics, aggregations, and mart tables';

-- Schema 5: USERS - User-related data
CREATE SCHEMA IF NOT EXISTS users
    COMMENT = 'User profiles, saved jobs, preferences, and alerts';

-- Verify
SHOW SCHEMAS IN DATABASE job_intelligence;

SELECT 'All schemas created successfully!' as status;
