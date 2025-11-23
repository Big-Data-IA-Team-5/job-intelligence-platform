-- Create raw data tables
USE DATABASE JOB_INTELLIGENCE;
USE SCHEMA RAW;
USE ROLE ACCOUNTADMIN;

-- Jobs table for scraped job postings
CREATE TABLE IF NOT EXISTS JOBS (
    job_id VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    title VARCHAR(500),
    company_name VARCHAR(500),
    location VARCHAR(500),
    description TEXT,
    posted_date TIMESTAMP_NTZ,
    salary_range VARCHAR(200),
    job_type VARCHAR(100),
    url TEXT,
    scraped_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (job_id, source)
) COMMENT = 'Raw scraped job postings';

-- H1B data table
CREATE TABLE IF NOT EXISTS H1B_DATA (
    case_number VARCHAR(50) PRIMARY KEY,
    case_status VARCHAR(50),
    employer_name VARCHAR(500),
    job_title VARCHAR(500),
    soc_code VARCHAR(20),
    soc_title VARCHAR(500),
    worksite_city VARCHAR(200),
    worksite_state VARCHAR(50),
    prevailing_wage NUMBER(12,2),
    wage_unit VARCHAR(50),
    fiscal_year INTEGER,
    received_date DATE,
    decision_date DATE,
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
) COMMENT = 'H1B visa application data from USCIS';

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON JOBS(posted_date);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON JOBS(company_name);
CREATE INDEX IF NOT EXISTS idx_h1b_employer ON H1B_DATA(employer_name);
CREATE INDEX IF NOT EXISTS idx_h1b_fiscal_year ON H1B_DATA(fiscal_year);

GRANT SELECT, INSERT, UPDATE ON TABLE JOBS TO ROLE SYSADMIN;
GRANT SELECT, INSERT, UPDATE ON TABLE H1B_DATA TO ROLE SYSADMIN;
