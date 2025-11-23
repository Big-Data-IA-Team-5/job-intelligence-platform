# Architecture

## System Overview

The Job Intelligence Platform is built using a modern data stack architecture:

```
┌─────────────────┐
│  Job Sources    │
│  (Indeed, etc)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Apache Airflow │ ◄── Orchestration
│   (Scheduler)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Snowflake     │
│   (Data Lake)   │
├─────────────────┤
│  RAW Schema     │ ◄── Ingested data
│  STAGING Schema │ ◄── Initial transforms
│  PROCESSING     │ ◄── Enrichment & AI
│  MARTS Schema   │ ◄── Final analytics
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      DBT        │ ◄── Transformations
│ (Data Modeling) │
└────────┬────────┘
         │
         ▼
┌─────────────────┬─────────────────┐
│   FastAPI       │    Streamlit    │
│   (Backend)     │    (Frontend)   │
└─────────────────┴─────────────────┘
```

## Components

### 1. Data Ingestion Layer
- **Scrapers**: Custom Python scrapers for job boards
- **Airflow DAGs**: Orchestrate daily scraping jobs
- **Snowflake RAW tables**: Store raw scraped data

### 2. Data Processing Layer
- **DBT Models**: Transform and enrich data
- **Snowflake Cortex**: AI-powered classification and embeddings
- **H1B Matching**: Join job postings with H1B sponsorship data

### 3. AI/ML Layer
- **Vector Embeddings**: Generate embeddings using Cortex
- **Semantic Search**: Similarity-based job matching
- **Classification**: Categorize jobs by type, seniority, etc.
- **Resume Matching**: Match resumes to jobs using vector similarity

### 4. Application Layer
- **FastAPI Backend**: RESTful API for all operations
- **Streamlit Frontend**: Interactive web application
- **Authentication**: User management (planned)

## Data Flow

1. **Daily Scraping** (2 AM):
   - Airflow triggers scraper DAG
   - Jobs scraped from multiple sources
   - Data loaded into Snowflake RAW schema

2. **Data Transformation** (Post-scraping):
   - DBT staging models deduplicate data
   - Processing models enrich with H1B data
   - Cortex generates embeddings and classifications

3. **User Interaction**:
   - User searches via Streamlit frontend
   - API fetches from Snowflake MARTS
   - Results ranked by relevance or similarity

## Technology Stack

### Data & Storage
- **Snowflake**: Cloud data warehouse
- **PostgreSQL**: Airflow metadata

### Orchestration & Processing
- **Apache Airflow**: Workflow orchestration
- **DBT**: Data transformation
- **Snowflake Cortex**: AI/ML functions

### Application
- **FastAPI**: Backend API framework
- **Streamlit**: Frontend framework
- **Python**: Primary language

### DevOps
- **Docker**: Containerization
- **GitHub Actions**: CI/CD
- **Git**: Version control

## Security Considerations

- Credentials stored in environment variables
- Snowflake role-based access control
- API authentication (to be implemented)
- No PII stored without encryption

## Scalability

- Snowflake auto-scales compute
- Airflow distributed execution
- API can be horizontally scaled
- Stateless frontend design

## Future Enhancements

1. **Real-time Processing**: Stream processing for instant job alerts
2. **Advanced ML**: Custom models for better matching
3. **Multi-tenancy**: Support for multiple users/organizations
4. **Mobile App**: Native mobile experience
5. **Job Alerts**: Email/SMS notifications
