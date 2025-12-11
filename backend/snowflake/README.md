# Snowflake Integration Guide

## Overview

This directory contains Snowflake setup scripts, agents, and configuration for the Job Intelligence Platform. The platform leverages Snowflake's data warehouse capabilities along with Cortex AI functions for semantic search, classification, and matching.

## Directory Structure

```
snowflake/
├── setup/              # SQL scripts for database setup
├── agents/            # Python agents for job processing
├── INTEGRATION.md     # Detailed integration documentation
└── README.md         # This file
```

## Prerequisites

- Snowflake account with appropriate privileges
- Python 3.8 or higher
- Snowflake Connector for Python
- Access to Cortex AI functions (SNOWFLAKE.CORTEX schema)

## Setup Instructions

### 1. Database Setup

Run the SQL scripts in the `setup/` directory **in order**:

```sql
-- Step 1: Create database and basic configuration
@setup/01_database_setup.sql

-- Step 2: Create schemas (RAW, PROCESSED, MARTS, USER_DATA)
@setup/02_schemas.sql

-- Step 3: Create raw data tables
@setup/03_raw_tables.sql

-- Step 4: Create processed tables with embeddings
@setup/04_processed_tables.sql

-- Step 5: Create user-related tables
@setup/05_user_tables.sql
```

**Important**: Execute each script sequentially. Verify success before proceeding to the next script.

### 2. Configure Environment

Create a `secrets.json` file in the project root with your Snowflake credentials:

```json
{
  "snowflake": {
    "account": "your-account",
    "user": "your-username",
    "password": "your-password",
    "warehouse": "JOB_INTEL_WH",
    "database": "JOB_INTELLIGENCE",
    "schema": "RAW",
    "role": "ACCOUNTADMIN"
  }
}
```

### 3. Install Dependencies

```bash
pip install -r snowflake/requirements.txt
```

### 4. Test Connection

```bash
python scripts/test_connections.py
```

## Table Descriptions

### RAW Schema

#### `JOBS`
Stores raw job posting data scraped from various sources.

| Column | Type | Description |
|--------|------|-------------|
| JOB_ID | VARCHAR | Unique identifier for the job |
| TITLE | VARCHAR | Job title |
| COMPANY | VARCHAR | Company name |
| LOCATION | VARCHAR | Job location |
| DESCRIPTION | TEXT | Full job description |
| SALARY_MIN | NUMBER | Minimum salary |
| SALARY_MAX | NUMBER | Maximum salary |
| JOB_TYPE | VARCHAR | Full-time, Part-time, Contract, etc. |
| EXPERIENCE_LEVEL | VARCHAR | Entry, Mid, Senior, etc. |
| POSTED_DATE | TIMESTAMP | When the job was posted |
| SOURCE_URL | VARCHAR | Original job posting URL |
| SCRAPED_AT | TIMESTAMP | When the data was scraped |

#### `H1B_EMPLOYERS`
H1B visa sponsorship data for employers.

| Column | Type | Description |
|--------|------|-------------|
| EMPLOYER_NAME | VARCHAR | Company name |
| FISCAL_YEAR | NUMBER | H1B fiscal year |
| INITIAL_APPROVALS | NUMBER | Number of initial approvals |
| CONTINUING_APPROVALS | NUMBER | Number of continuing approvals |
| TOTAL_APPROVALS | NUMBER | Total approvals |

### PROCESSED Schema

#### `EMBEDDED_JOBS`
Jobs with semantic embeddings for search and matching.

| Column | Type | Description |
|--------|------|-------------|
| JOB_ID | VARCHAR | Foreign key to RAW.JOBS |
| EMBEDDING | VECTOR | 768-dimensional embedding vector |
| PROCESSED_AT | TIMESTAMP | Processing timestamp |

#### `CLASSIFIED_JOBS`
Jobs with AI-generated classifications and categories.

| Column | Type | Description |
|--------|------|-------------|
| JOB_ID | VARCHAR | Foreign key to RAW.JOBS |
| CATEGORY | VARCHAR | Job category (e.g., Engineering, Sales) |
| SUBCATEGORY | VARCHAR | More specific classification |
| REQUIRED_SKILLS | ARRAY | List of required skills |
| PREFERRED_SKILLS | ARRAY | List of preferred skills |
| SENIORITY_LEVEL | VARCHAR | Extracted seniority level |
| CLASSIFICATION_METADATA | VARIANT | Additional classification data |
| CLASSIFIED_AT | TIMESTAMP | Classification timestamp |

#### `H1B_MATCHED_JOBS`
Jobs matched with H1B sponsorship likelihood.

| Column | Type | Description |
|--------|------|-------------|
| JOB_ID | VARCHAR | Foreign key to RAW.JOBS |
| EMPLOYER_NAME | VARCHAR | Matched employer name |
| H1B_LIKELIHOOD | VARCHAR | High, Medium, Low |
| MATCH_SCORE | NUMBER | Confidence score (0-1) |
| HISTORICAL_APPROVALS | NUMBER | Past H1B approvals |
| MATCHED_AT | TIMESTAMP | Matching timestamp |

### MARTS Schema

#### `JOB_INTELLIGENCE_MART`
Consolidated view combining all job data, classifications, and H1B information.

### USER_DATA Schema

#### `USER_PROFILES`
User account information and preferences.

#### `SAVED_JOBS`
Jobs saved by users for later review.

#### `USER_SEARCHES`
Search history for analytics and personalization.

#### `USER_RESUMES`
Resume embeddings for job matching.

## Agent Documentation

### Agent 1: Semantic Search Agent

**Location**: `agents/agent1_search.py`

**Purpose**: Performs semantic search on job postings using natural language queries.

**Key Features**:
- Natural language query processing
- Vector similarity search using Cortex AI embeddings
- Configurable result limits and similarity thresholds
- Integration with Snowflake Cortex EMBED_TEXT_768 function

**Usage**:

```python
from snowflake.agents.agent1_search import JobSearchAgent

# Initialize agent
agent = JobSearchAgent()

# Search for jobs
results = agent.search("Python developer with machine learning experience")

# Search with filters
results = agent.search("CPT internships", filters={'limit': 10})

# Close connection when done
agent.close()
```

**API Response Format**:

```python
{
    'status': 'success',
    'total': 10,
    'jobs': [
        {
            'JOB_ID': 'JOB_123',
            'TITLE': 'Software Engineer',
            'COMPANY': 'Tech Corp',
            'LOCATION': 'San Francisco, CA',
            'DESCRIPTION': '...',
            'VISA_CATEGORY': 'CPT',
            'H1B_SPONSOR': True,
            # ... other fields
        }
    ]
}
```

**Semantic Model**: `agents/agent1_semantic_model.yaml`

Defines the semantic layer for Agent 1, including:
- Database tables and relationships
- Query dimensions and filters
- Natural language mappings

### Agent 3: Job Classification Agent

**Location**: `agents/agent3_classifier.py`

**Purpose**: Automatically classifies jobs and extracts structured information.

**Key Features**:
- Category and subcategory classification
- Skill extraction (required and preferred)
- Seniority level detection
- Leverages Cortex AI COMPLETE function

**Usage**:

```python
from snowflake.agents.agent3_classifier import classify_job

classification = classify_job(job_id="JOB_123")
```

### Agent 4: H1B Matching Agent

**Location**: `agents/agent4_matcher.py`

**Purpose**: Matches jobs with H1B sponsorship likelihood based on historical data.

**Key Features**:
- Employer name matching with fuzzy logic
- H1B likelihood scoring
- Historical approval data integration

**Usage**:

```python
from snowflake.agents.agent4_matcher import match_h1b_likelihood

h1b_info = match_h1b_likelihood(job_id="JOB_123")
```

## Integration Guide

### Quick Integration Steps

1. **Set up Snowflake environment** using the setup scripts
2. **Configure connection** in your application using the `snowflake_client.py` utility
3. **Load initial data** using the scrapers
4. **Run agents** to process and enrich job data
5. **Query results** through the MARTS layer or API endpoints

### API Integration

The platform provides REST API endpoints for interacting with Snowflake data:

```python
# Backend API client
from app.utils.snowflake_client import SnowflakeClient

client = SnowflakeClient()
jobs = client.execute_query("SELECT * FROM MARTS.JOB_INTELLIGENCE_MART LIMIT 10")
```

### Frontend Integration

The Streamlit frontend connects to the backend API:

```python
# Frontend API client
from utils.api_client import APIClient

api = APIClient()
search_results = api.search_jobs(query="data engineer", limit=20)
```

### DBT Integration

Use DBT for transformation pipelines. See `dbt/` directory for models and configuration.

```bash
# Run DBT transformations
cd dbt
dbt run
dbt test
```

## Testing

Run the test suite to verify Agent 1 functionality:

```bash
python -m pytest tests/test_agent1.py -v
```

Or run directly:

```bash
python tests/test_agent1.py
```

## Troubleshooting

### Common Issues

**Connection Errors**:
- Verify credentials in `secrets.json`
- Check network connectivity to Snowflake
- Ensure warehouse is running

**Embedding Errors**:
- Verify Cortex AI access in your Snowflake account
- Check that SNOWFLAKE.CORTEX schema is available
- Ensure proper role permissions

**Performance Issues**:
- Consider creating indexes on frequently queried columns
- Use appropriate warehouse size for workload
- Optimize vector search with similarity thresholds

**Import Errors**:
- Ensure all dependencies are installed: `pip install -r snowflake/requirements.txt`
- Check Python path configuration
- Verify module structure is correct

## Additional Resources

- [Snowflake Cortex AI Documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex)
- [Vector Search in Snowflake](https://docs.snowflake.com/en/user-guide/vector-search)
- [INTEGRATION.md](./INTEGRATION.md) - Detailed integration documentation

## Support

For issues or questions, please refer to the main project README or open an issue in the repository.
