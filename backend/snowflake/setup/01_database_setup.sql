-- ============================================
-- FILE 1: 01_database_setup.sql
-- Database and Warehouse Creation
-- ============================================

USE ROLE ACCOUNTADMIN;

-- Create main database
CREATE DATABASE IF NOT EXISTS job_intelligence
    COMMENT = 'Job Intelligence Platform - DAMG 7245 Final Project';

-- Create compute warehouse (main)
CREATE WAREHOUSE IF NOT EXISTS compute_wh
    WAREHOUSE_SIZE = 'X-SMALL'
    AUTO_SUSPEND = 60                    -- Suspend after 1 minute idle
    AUTO_RESUME = TRUE                   -- Auto-resume on query
    INITIALLY_SUSPENDED = TRUE           -- Start suspended (save costs)
    COMMENT = 'Main compute warehouse for queries and agents';

-- Create loading warehouse (optional - for heavy ETL)
CREATE WAREHOUSE IF NOT EXISTS loading_wh
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Warehouse for data loading and transformations';

-- Set context
USE DATABASE job_intelligence;
USE WAREHOUSE compute_wh;

-- Verify
SELECT 
    CURRENT_DATABASE() as database,
    CURRENT_WAREHOUSE() as warehouse,
    'Database and warehouses created successfully!' as status;

SHOW DATABASES LIKE 'job_intelligence';
SHOW WAREHOUSES;