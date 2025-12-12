# 🏗️ Job Intelligence Platform - Technical Architecture

> **Complete System Documentation**: Database schemas, data pipelines, AI agents, resume processing, and job matching algorithms

**Last Updated**: December 12, 2025  
**System Status**: Production Ready ✅

---

## 📑 Table of Contents

1. [System Overview](#system-overview)
2. [Database Architecture](#database-architecture)
3. [Data Pipeline Flow](#data-pipeline-flow)
4. [Resume Processing](#resume-processing)
5. [Job Matching Algorithms](#job-matching-algorithms)
6. [Backend API Architecture](#backend-api-architecture)
7. [AI Agents System](#ai-agents-system)
8. [Frontend Stack](#frontend-stack)

---

## 🎯 System Overview

### Architecture Stack

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                    │
│  Streamlit App (Cloud Run) - User Interface         │
│  • Jobs Database • Analytics • Chat • Resume Match   │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓ HTTPS/REST API
┌─────────────────────────────────────────────────────┐
│                   BACKEND LAYER                      │
│   FastAPI (Cloud Run) - Business Logic              │
│   • /jobs • /resume • /chat • /analytics             │
└────────────────┬────────────────────────────────────┘
                 │
                 ↓ JDBC/SQL
┌─────────────────────────────────────────────────────┐
│                  DATA LAYER                          │
│  Snowflake Cloud Data Warehouse                     │
│  • RAW schemas • STAGING • PROCESSED • ANALYTICS     │
│  • Snowflake Cortex AI (LLMs + Vector Embeddings)   │
└────────────────┬────────────────────────────────────┘
                 │
                 ↑ Ingestion (Airflow/Composer)
┌─────────────────────────────────────────────────────┐
│                 ORCHESTRATION LAYER                  │
│  Google Cloud Composer (Airflow)                    │
│  • Scrapers DAGs • dbt DAGs • Embedding Generation   │
└─────────────────────────────────────────────────────┘
```

### Key Technologies
- **Database**: Snowflake (Cloud Data Warehouse)
- **Backend**: FastAPI (Python)
- **Frontend**: Streamlit
- **Orchestration**: Apache Airflow (Google Cloud Composer)
- **Transformations**: dbt (data build tool)
- **AI/ML**: Snowflake Cortex (Mistral-Large2, e5-base-v2 embeddings)
- **Deployment**: Google Cloud Run
- **Storage**: Google Cloud Storage (GCS)

---

## 🗄️ Database Architecture

### Snowflake Database: `JOB_INTELLIGENCE`

#### Schema Structure

```
JOB_INTELLIGENCE/
├── RAW/                          # Raw ingested data
│   ├── JOBS_RAW                  # Scraped job postings
│   └── H1B_RAW                   # H-1B visa sponsorship data
├── STAGING/                      # Cleaned & deduplicated
│   ├── STG_JOBS                  # Cleaned jobs (view)
│   └── DEDUP_JOBS                # Deduplicated jobs (view)
├── PROCESSED_PROCESSING/         # Intermediate transformations
│   ├── CLASSIFIED_JOBS           # AI-classified jobs (table)
│   ├── H1B_MATCHED_JOBS          # Jobs matched with H-1B data (table)
│   └── EMBEDDED_JOBS             # Jobs with vector embeddings (table)
└── PROCESSED/                    # Production-ready data
    └── JOBS_PROCESSED            # Final enriched jobs table (table)
```

---

### 📊 Table Schemas

#### 1. **RAW.JOBS_RAW** - Source Job Postings

**Purpose**: Raw job data from web scrapers  
**Row Count**: ~50,000+ jobs  
**Retention**: Last 90 days

| Column | Type | Description |
|--------|------|-------------|
| `job_id` | STRING (PK) | Unique job identifier |
| `url` | STRING (UNIQUE) | Job posting URL |
| `title` | STRING | Job title |
| `company` | STRING | Company name |
| `location` | STRING | Job location |
| `description` | TEXT | Full job description |
| `snippet` | STRING | Brief job summary |
| `salary_min` | NUMBER(10,2) | Minimum salary |
| `salary_max` | NUMBER(10,2) | Maximum salary |
| `salary_text` | STRING | Original salary text |
| `job_type` | STRING | Full-time/Part-time/Contract/Internship |
| `posted_date` | DATE | When job was posted |
| `work_model` | VARCHAR(50) | Remote/Hybrid/On-site |
| `department` | VARCHAR(100) | Engineering/Sales/Marketing/etc. |
| `company_size` | VARCHAR(50) | Startup/Mid-size/Enterprise |
| `qualifications` | TEXT | Job requirements |
| `h1b_sponsored` | VARCHAR(10) | Yes/No/Unknown |
| `is_new_grad` | VARCHAR(10) | Yes/No |
| `category` | VARCHAR(100) | Job category |
| `scraped_at` | TIMESTAMP_NTZ | Ingestion timestamp |
| `source` | STRING | fortune500/airtable/comprehensive/internship |

**Indexes**: company, scraped_at, location, work_model, h1b_sponsored

**Data Sources**:
- Fortune 500 company career pages
- Airtable comprehensive scraper
- Airtable internship scraper
- Airtable graduate job scraper

---

#### 2. **RAW.H1B_RAW** - H-1B Visa Sponsorship Data

**Purpose**: USCIS H-1B LCA certification data  
**Row Count**: 479,005 records (FY2025 Q3)  
**Source**: Department of Labor LCA Disclosure Data

| Column | Type | Description |
|--------|------|-------------|
| `case_number` | STRING (PK) | LCA case number |
| `case_status` | STRING | Certified/Denied/Withdrawn |
| `employer_name` | STRING | Company name |
| `job_title` | STRING | Position title |
| `soc_title` | STRING | Standard Occupational Classification |
| `worksite_city` | STRING | Work location city |
| `worksite_state` | STRING | Work location state |
| `wage_rate_of_pay_from` | NUMBER(10,2) | Minimum wage |
| `wage_rate_of_pay_to` | NUMBER(10,2) | Maximum wage |
| `wage_unit_of_pay` | STRING | Year/Hour/Week/Month |
| `h1b_dependent` | STRING | High visa dependency flag (Y/N) |
| `willful_violator` | STRING | Immigration violations flag (Y/N) |
| `loaded_at` | TIMESTAMP_NTZ | Data load timestamp |

**Additional H-1B Fields** (97 columns total):
- Employer contact information (POC name, email, phone)
- Employer address details
- Prevailing wage data
- Employment details (full-time, new/continued employment)
- NAICS codes

---

#### 3. **PROCESSED.JOBS_PROCESSED** - Final Enriched Jobs

**Purpose**: Production-ready jobs with AI enrichments and H-1B matching  
**Materialization**: Table (incrementally updated)  
**Row Count**: ~40,000+ jobs

| Column | Type | Description |
|--------|------|-------------|
| **Core Fields** | | |
| `job_id` | STRING (PK) | Unique identifier |
| `title` | STRING | Job title |
| `company` | STRING | Company name |
| `location` | STRING | Job location |
| `description` | TEXT | Full description |
| `snippet` | STRING | Brief summary |
| `url` | STRING | Job posting URL |
| `source` | STRING | Data source |
| **Salary & Compensation** | | |
| `salary_min` | NUMBER | Minimum salary |
| `salary_max` | NUMBER | Maximum salary |
| `salary_text` | STRING | Original salary text |
| **Job Classification** | | |
| `job_type` | STRING | Employment type |
| `work_model` | STRING | Remote/Hybrid/On-site |
| `job_category` | STRING | AI-classified category |
| `department` | STRING | Department/function |
| `seniority_level` | STRING | Junior/Mid/Senior/Principal |
| `is_new_grad_role` | BOOLEAN | New grad friendly |
| **H-1B Sponsorship** | | |
| `h1b_sponsor` | BOOLEAN | Is H-1B sponsor |
| `h1b_employer_name` | STRING | Matched H-1B employer |
| `h1b_city` | STRING | H-1B worksite city |
| `h1b_state` | STRING | H-1B worksite state |
| `h1b_total_petitions` | NUMBER | Total H-1B filings |
| `h1b_approval_rate` | FLOAT | Approval rate (0-1) |
| `h1b_avg_wage` | NUMBER | Average H-1B wage |
| `sponsorship_score` | FLOAT | Sponsorship likelihood |
| `h1b_risk_level` | STRING | Low/Medium/High |
| `visa_category` | STRING | H-1B/OPT/CPT |
| **AI Enrichments** | | |
| `description_embedding` | VECTOR(FLOAT, 768) | Semantic embedding |
| `extracted_skills` | STRING | AI-extracted skills |
| `classification_confidence` | FLOAT | AI confidence score |
| **Metadata** | | |
| `posted_date` | DATE | Posting date |
| `days_since_posted` | NUMBER | Freshness metric |
| `scraped_at` | TIMESTAMP_NTZ | Scrape timestamp |
| `processed_at` | TIMESTAMP_NTZ | Processing timestamp |

**Key Indexes**: job_id, company, location, h1b_sponsor, days_since_posted

---

## 🔄 Data Pipeline Flow

### End-to-End Pipeline

```
┌──────────────────────────────────────────────────────────┐
│ STEP 1: INGESTION (Airflow DAGs)                         │
│ ─────────────────────────────────────────────────────    │
│ • Fortune 500 Scraper      → JOBS_RAW                    │
│ • Airtable Comprehensive   → JOBS_RAW                    │
│ • Airtable Internships     → JOBS_RAW                    │
│ • H-1B CSV Upload          → H1B_RAW                     │
│ Frequency: Daily (2 AM UTC)                              │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 2: STAGING (dbt models)                             │
│ ─────────────────────────────────────────────────────    │
│ • STG_JOBS: Clean & type cast raw data                   │
│ • DEDUP_JOBS: Remove duplicates (by job_id + source)     │
│ Materialization: VIEW (no storage)                       │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 3: H-1B MATCHING (dbt model)                        │
│ ─────────────────────────────────────────────────────    │
│ • H1B_MATCHED_JOBS: Join jobs with H-1B sponsors         │
│   - Match algorithm: UPPER(TRIM(company)) fuzzy match    │
│   - Priority: exact > contains > reverse contains        │
│   - Deduplication: Best match per job_id                 │
│   - Metrics: approval_rate, total_petitions              │
│ Materialization: TABLE (incremental)                     │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 4: AI CLASSIFICATION (dbt model + Cortex)           │
│ ─────────────────────────────────────────────────────    │
│ • CLASSIFIED_JOBS: AI-powered job classification         │
│   - LLM: Mistral-Large (Snowflake Cortex)               │
│   - Classifications:                                     │
│     * job_category: Engineering/Data/Product/etc.        │
│     * seniority_level: Junior/Mid/Senior/Principal       │
│     * is_remote: TRUE/FALSE                              │
│     * extracted_skills: Top 5 technical skills           │
│ Materialization: TABLE (incremental)                     │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 5: VECTOR EMBEDDINGS (dbt model + Cortex)           │
│ ─────────────────────────────────────────────────────    │
│ • EMBEDDED_JOBS: Generate semantic embeddings            │
│   - Model: e5-base-v2 (768 dimensions)                   │
│   - Embeddings:                                          │
│     * description_embedding: title + company + desc      │
│     * skills_embedding: extracted_skills text            │
│   - Used for: Semantic search, resume matching           │
│ Materialization: TABLE (incremental)                     │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 6: FINAL SYNC (Python script)                       │
│ ─────────────────────────────────────────────────────    │
│ • generate_embeddings.py: Sync to JOBS_PROCESSED         │
│   - Merges EMBEDDED_JOBS + JOBS_RAW columns              │
│   - Adds computed fields: days_since_posted              │
│   - MERGE operation: INSERT new, UPDATE existing         │
│   - Batch processing: 100 jobs per batch                 │
│ Run frequency: Every 6 hours                             │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ FINAL OUTPUT: JOBS_PROCESSED (Production Table)          │
│ Ready for: API queries, semantic search, analytics       │
└──────────────────────────────────────────────────────────┘
```

### Pipeline Execution Times
- **Ingestion**: ~15-30 minutes (depends on scraper)
- **dbt transformations**: ~5-10 minutes
- **Embedding generation**: ~20-40 minutes (depends on new jobs)
- **Total pipeline**: ~1-2 hours end-to-end

---

## 👤 Resume Processing

### Agent 4: Resume Matcher Architecture

**File**: `snowflake/agents/agent4_matcher.py`

#### How Resume Matching Works

```
┌──────────────────────────────────────────────────────────┐
│ INPUT: Resume Text (PDF/DOCX → parsed text)              │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 1: PROFILE EXTRACTION (LLM)                          │
│ ─────────────────────────────────────────────────────    │
│ Model: Mistral-Large2 (Snowflake Cortex)                │
│                                                          │
│ Extracted Data:                                          │
│ • technical_skills: ["Python", "AWS", "React", ...]     │
│ • soft_skills: ["Leadership", "Communication", ...]      │
│ • total_experience_years: 3.5                            │
│ • education_level: "Master's in Computer Science"        │
│ • work_authorization: "F-1 OPT" / "H-1B" / "US Citizen" │
│ • desired_roles: ["Software Engineer", "SWE", ...]      │
│ • preferred_locations: ["Boston", "NYC", "Remote"]       │
│ • salary_min: 85000                                      │
│                                                          │
│ Prompt Engineering:                                      │
│ - Comprehensive skill categorization                     │
│ - Experience calculation (sum all durations)             │
│ - Visa status inference from keywords                    │
│ - Location & salary extraction                           │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 2: VECTOR SEARCH (Semantic Similarity)              │
│ ─────────────────────────────────────────────────────    │
│ 1. Generate resume embedding:                            │
│    embedding = EMBED_TEXT_768(                           │
│      'e5-base-v2',                                       │
│      skills + desired_roles + experience                 │
│    )                                                     │
│                                                          │
│ 2. Vector similarity search:                             │
│    SELECT job_id, title, company, location,              │
│           VECTOR_COSINE_SIMILARITY(                      │
│             description_embedding,                       │
│             resume_embedding                             │
│           ) AS similarity_score                          │
│    FROM JOBS_PROCESSED                                   │
│    WHERE similarity_score > 0.6  -- Threshold            │
│    ORDER BY similarity_score DESC                        │
│    LIMIT 20  -- Top 20 candidates                        │
│                                                          │
│ Returns: Top 20 jobs with highest semantic similarity    │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ STEP 3: AI RE-RANKING (Sophisticated Scoring)            │
│ ─────────────────────────────────────────────────────    │
│ Model: Mistral-Large2 (Advanced reasoning)              │
│                                                          │
│ Scoring Framework (0-100 points each):                  │
│                                                          │
│ 1. Skills Match (35% weight):                           │
│    • Exact matches: +10 points each                     │
│    • Similar/transferable: +5 points                    │
│    • Rare skill bonus: +20                              │
│    • Missing critical: -5                               │
│                                                          │
│ 2. Experience Fit (30% weight):                         │
│    • Perfect match (±1 year): 100                       │
│    • Within range (±2 years): 80                        │
│    • Over-qualified (+2-4 years): 70                    │
│    • Under-qualified: 60                                │
│                                                          │
│ 3. Visa Compatibility (20% weight):                     │
│    • H-1B sponsor + needs H-1B: 100                     │
│    • US Citizen: 100 (any job)                          │
│    • OPT + accepts OPT: 100                             │
│    • No visa support: 0                                 │
│                                                          │
│ 4. Location Match (10% weight):                         │
│    • Exact city match: 100                              │
│    • Remote job: 100                                    │
│    • Same state: 70                                     │
│    • Different region: 40                               │
│                                                          │
│ 5. Career Growth (5% weight):                           │
│    • Clear advancement path: 90+                        │
│    • Skill expansion: 80                                │
│    • Lateral move: 60                                   │
│                                                          │
│ LLM Output: JSON with scores + reasoning for each job   │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ OUTPUT: Top 10 Job Matches                               │
│ ─────────────────────────────────────────────────────    │
│ Each match includes:                                     │
│ • overall_score: 87/100                                  │
│ • skills_score: 92/100                                   │
│ • experience_score: 85/100                               │
│ • visa_score: 100/100                                    │
│ • location_score: 75/100                                 │
│ • reasoning: "Excellent Python/AWS match (8/10 skills),  │
│              H-1B sponsor with 95% approval..."          │
└──────────────────────────────────────────────────────────┘
```

#### Example API Call

**Endpoint**: `POST /api/resume/match`

```json
{
  "resume_text": "John Doe\n\nEDUCATION:\nMaster's in Computer Science, MIT\n\nEXPERIENCE:\nSoftware Engineer at Amazon (2 years)\n- Built microservices with Python/AWS\n- Led team of 3 engineers\n\nSKILLS:\nPython, Java, AWS, Docker, Kubernetes, React\n\nVISA STATUS: F-1 OPT",
  "user_id": "user_123"
}
```

**Response**:
```json
{
  "status": "success",
  "profile": {
    "technical_skills": ["Python", "Java", "AWS", "Docker", "Kubernetes", "React"],
    "soft_skills": ["Leadership", "Team Management"],
    "total_experience_years": 2.0,
    "education_level": "Master's in Computer Science",
    "work_authorization": "F-1 OPT",
    "desired_roles": ["Software Engineer"],
    "preferred_locations": ["Remote"],
    "salary_min": 90000
  },
  "top_matches": [
    {
      "job_id": "abc123",
      "title": "Senior Software Engineer",
      "company": "Google",
      "location": "Mountain View, CA (Remote available)",
      "overall_score": 0.92,
      "skills_score": 0.95,
      "experience_score": 0.88,
      "visa_score": 1.0,
      "location_score": 1.0,
      "match_reasoning": "Excellent Python/AWS match (6/6 core skills), H-1B sponsor with 98% approval rate, remote-friendly, clear path to senior role",
      "url": "https://google.com/careers/123"
    }
  ]
}
```

---

## 🔍 Job Matching Algorithms

### Semantic Search (Vector Embeddings)

**Technology**: Snowflake Cortex + e5-base-v2 model

#### How It Works

1. **Embedding Generation**:
   ```sql
   SELECT SNOWFLAKE.CORTEX.EMBED_TEXT_768(
       'e5-base-v2',
       CONCAT(title, '. ', company, '. ', LEFT(description, 2000))
   ) AS description_embedding
   ```

2. **Similarity Search**:
   ```sql
   SELECT job_id, title, company,
          VECTOR_COSINE_SIMILARITY(
              description_embedding,
              :query_embedding
          ) AS similarity_score
   FROM JOBS_PROCESSED
   WHERE similarity_score > 0.6
   ORDER BY similarity_score DESC
   LIMIT 10
   ```

3. **Why Vector Embeddings?**
   - Understands semantic meaning (not just keywords)
   - "data scientist" matches "machine learning engineer"
   - "python developer" matches "backend engineer"
   - Captures context from full job description

---

### Natural Language Search (Agent 1)

**File**: `snowflake/agents/agent1_search.py`

#### Query Processing Flow

```
User Query: "remote python jobs in Boston with H-1B sponsorship"
                        ↓
┌──────────────────────────────────────────────────────────┐
│ LLM Intent Parsing (Mistral-Large2)                      │
│ ─────────────────────────────────────────────────────    │
│ Extracted Entities:                                      │
│ • job_titles: ["Python Developer", "Backend Engineer"]  │
│ • skills: ["Python"]                                     │
│ • locations: ["Boston"]                                  │
│ • work_model: "Remote"                                   │
│ • visa_required: true                                    │
└──────────────────────────────────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────────┐
│ SQL Generation                                           │
│ ─────────────────────────────────────────────────────    │
│ SELECT * FROM jobs_processed                             │
│ WHERE (                                                  │
│   LOWER(title) LIKE '%python%'                          │
│   OR LOWER(title) LIKE '%backend engineer%'             │
│ )                                                        │
│ AND (                                                    │
│   LOWER(location) LIKE '%boston%'                       │
│   OR work_model = 'Remote'                              │
│ )                                                        │
│ AND h1b_sponsor = TRUE                                  │
│ ORDER BY scraped_at DESC                                │
│ LIMIT 50                                                │
└──────────────────────────────────────────────────────────┘
```

---

## 🔌 Backend API Architecture

### FastAPI Routes

**Deployment**: Google Cloud Run  
**URL**: `https://job-intelligence-backend-97083220044.us-central1.run.app`

#### API Endpoints

##### 1. **Jobs Search** - `/api/jobs/search`

**Method**: POST  
**Purpose**: Advanced job filtering and search

**Request Body**:
```json
{
  "search": "python engineer",
  "companies": ["Google", "Amazon"],
  "locations": ["San Francisco", "Remote"],
  "work_models": ["Remote", "Hybrid"],
  "visa_sponsorship": "Yes",
  "salary_min": 100000,
  "salary_max": 200000,
  "posted_within_days": 7,
  "job_types": ["Full-time"],
  "sort_by": "most_recent",
  "limit": 50
}
```

**Filters Implementation**:
```python
# Date filter (fixed to use days_since_posted)
if filters.posted_within_days:
    where_clauses.append(
        f"(days_since_posted <= {filters.posted_within_days})"
    )

# Visa sponsorship filter
if filters.visa_sponsorship == "Yes":
    where_clauses.append("h1b_sponsor = TRUE")

# Salary range filter
if filters.salary_min:
    where_clauses.append(
        f"(salary_min >= {filters.salary_min} OR salary_max >= {filters.salary_min})"
    )

# LLM-enhanced search (expands keywords semantically)
if filters.search:
    # Use Mistral to find synonyms
    # "software engineer" → ["SWE", "Developer", "Programmer"]
    enhanced_terms = llm_expand_search(filters.search)
```

**Response**:
```json
{
  "jobs": [...],
  "total": 127,
  "filters_applied": {...}
}
```

---

##### 2. **Resume Matching** - `/api/resume/match`

**Method**: POST  
**Purpose**: Match resume to top 10 jobs

See [Resume Processing](#resume-processing) section for details.

---

##### 3. **Analytics** - `/api/analytics/*`

**Endpoints**:
- `GET /analytics/summary` - Overall platform stats
- `GET /analytics/trends` - Job posting trends (time series)
- `GET /analytics/companies` - Top hiring companies
- `GET /analytics/locations` - Jobs by location
- `GET /analytics/skills` - Top in-demand skills

**Example**: `/analytics/summary`
```json
{
  "total_jobs": 42153,
  "total_companies": 8742,
  "h1b_sponsors": 3254,
  "avg_salary": 98750,
  "recent_postings_7d": 1834
}
```

---

##### 4. **Chat Agent** - `/api/chat/ask`

**Method**: POST  
**Purpose**: Intelligent Q&A about jobs, companies, H-1B data

**Capabilities**:
- Job search: "data engineer jobs in Boston"
- Salary queries: "what's the salary for SDE at Amazon?"
- H-1B info: "does Google sponsor H-1B?"
- Company comparisons: "compare Microsoft vs Meta"
- Contact info: "who should I contact at Amazon?"

**Agent 2 Intelligence** (see [AI Agents](#ai-agents-system)):
- Full schema awareness (97 H-1B columns, 40+ job fields)
- LLM intent detection
- Entity extraction (job title, location, company)
- Resume context integration
- Multi-turn conversation handling

---

## 🤖 AI Agents System

### Agent 1: Search Agent

**File**: `snowflake/agents/agent1_search.py`  
**Purpose**: Natural language → SQL job search

**Key Features**:
- Parse user queries using Mistral-Large2
- Extract entities (titles, skills, locations, visa needs)
- Generate optimized SQL queries
- Return ranked results

**Example**:
```python
agent1 = JobSearchAgent()
result = agent1.search(
    query="remote senior python jobs",
    filters={"visa_status": "h1b", "salary_min": 120000}
)
```

---

### Agent 2: Chat Intelligence Agent

**File**: `snowflake/agents/agent2_chat.py`  
**Purpose**: Conversational job intelligence

**Intent Detection**:
- `job_search` → Route to Agent 1
- `salary_info` → Query H-1B wage data
- `h1b_sponsorship` → Check sponsor status
- `company_comparison` → Multi-company analysis
- `contact_info` → Retrieve POC details

**Context Awareness**:
- Maintains conversation history
- Resume context (skills, experience)
- Follow-up question handling

**Example**:
```python
agent2 = JobIntelligenceAgent()
result = agent2.ask(
    question="what's the average salary for data scientists at Amazon?",
    resume_context="5 years Python, ML experience",
    chat_history=[...]
)
```

---

### Agent 4: Resume Matcher

**File**: `snowflake/agents/agent4_matcher.py`

See [Resume Processing](#resume-processing) section for complete details.

---

## 🖥️ Frontend Stack

**Technology**: Streamlit  
**Deployment**: Google Cloud Run  
**URL**: `https://job-intelligence-frontend-97083220044.us-central1.run.app`

### Pages

#### 1. **Jobs Database** (`pages/2_💼_Jobs_Database.py`)

**Features**:
- Advanced filtering (location, company, salary, visa, date)
- Real-time search with backend API
- Date filters: Last 24 hours / 7 days / 30 days / Any time
- Sort options: Most recent, Highest salary, Company A-Z, H-1B rate
- H-1B sponsor badges
- Direct apply links

**Filter Implementation**:
```python
# Date filter mapping
posted_days_map = {
    'Any time': None,
    'Last 24 hours': 1,  # Shows jobs with days_since_posted <= 1
    'Last 7 days': 7,
    'Last 30 days': 30
}

# API call
response = requests.post(
    f"{BACKEND_URL}/api/jobs/search",
    json={
        "posted_within_days": posted_days_map[selected_timeframe],
        "companies": selected_companies,
        "locations": selected_locations,
        "visa_sponsorship": visa_filter,
        ...
    }
)
```

---

#### 2. **Advanced Analytics** (`pages/1_📊_Advanced_Analytics.py`)

**Visualizations**:
- Job posting trends (line chart)
- Top companies by job count (bar chart)
- Location distribution (map)
- Salary ranges by role (box plots)
- H-1B sponsor analysis
- Skill demand analysis

---

#### 3. **Chat Interface** (Agent 2)

**Features**:
- Natural language queries
- Resume context integration
- Conversation history
- Job result display
- AI intelligence display (intent, entities, confidence)

---

## 📈 Data Quality & Monitoring

### Data Quality Checks

1. **Deduplication**: 
   - By `job_id + source` (ROW_NUMBER() window function)
   - Keeps most recent scrape per job

2. **Validation**:
   - NOT NULL constraints on critical fields
   - Date range validation (last 90 days)
   - Salary sanity checks

3. **H-1B Matching Accuracy**:
   - 3-tier matching priority (exact > contains > reverse contains)
   - Deduplication by best match

### Pipeline Monitoring

**Airflow DAGs**:
- `dag_fortune500_scraper` - Daily at 2 AM
- `dag_airtable_comprehensive` - Daily at 3 AM
- `dag_airtable_internships` - Daily at 4 AM
- `dag_generate_embeddings` - Every 6 hours

**Alert Conditions**:
- DAG failure
- Row count drops >20%
- Embedding generation timeout
- Snowflake connection errors

---

## 🔐 Security & Access Control

### Snowflake

- **Role-Based Access**: ACCOUNTADMIN, SYSADMIN, READONLY
- **Network Policies**: IP whitelisting
- **OAuth**: Service account for backend
- **Encryption**: At-rest and in-transit

### Backend API

- **CORS**: Configured for frontend domain
- **Rate Limiting**: 100 req/min per IP
- **SQL Injection Prevention**: Parameterized queries
- **Input Validation**: Pydantic models

### Secrets Management

- **Google Secret Manager** for production
- **secrets.json** for local development (gitignored)

---

## 🚀 Deployment Architecture

### Cloud Services

```
Frontend (Streamlit)
├─ Google Cloud Run
├─ Region: us-central1
├─ Memory: 2Gi
├─ CPU: 2
└─ Auto-scaling: 0-10 instances

Backend (FastAPI)
├─ Google Cloud Run
├─ Region: us-central1
├─ Memory: 2Gi
├─ CPU: 2
└─ Auto-scaling: 0-10 instances

Orchestration (Airflow)
├─ Google Cloud Composer
├─ Environment: job-intel-airflow
└─ Scheduler: Cloud Composer managed

Database (Snowflake)
├─ Account: job-intelligence-platform
├─ Warehouse: COMPUTE_WH (Medium)
└─ Storage: ~50 GB
```

### CI/CD

**Deployment Method**: Manual (gcloud CLI)

```bash
# Backend deployment
gcloud run deploy job-intelligence-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --timeout 300 \
  --memory 2Gi \
  --cpu 2

# Frontend deployment
gcloud run deploy job-intelligence-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars BACKEND_URL=https://job-intelligence-backend-...
```

---

## 📊 Performance Metrics

### Query Performance

- **Job search (filtered)**: 200-500ms
- **Resume matching**: 5-8 seconds
- **Vector similarity search**: 1-2 seconds
- **Analytics aggregations**: 300-800ms

### Data Freshness

- **Jobs data**: Updated daily
- **H-1B data**: Updated quarterly (USCIS release schedule)
- **Embeddings**: Generated within 6 hours of new jobs

---

## 🎯 Key Technical Decisions

### Why Snowflake?

- Native vector embeddings support
- Integrated LLM (Cortex) - no external API calls
- Scales to millions of rows
- SQL-native transformations (dbt)
- Built-in data sharing

### Why dbt?

- Version-controlled transformations
- Incremental models (efficient updates)
- Lineage tracking
- Testing framework

### Why Streamlit?

- Rapid prototyping
- Python-native (same language as backend)
- Built-in components (charts, filters)
- Easy deployment to Cloud Run

---

## 📝 Future Enhancements

1. **Real-time scraping** - Event-driven instead of batch
2. **Company profiles** - Enriched company data (funding, size, tech stack)
3. **Salary predictions** - ML model for salary estimation
4. **Job alerts** - Email notifications for saved searches
5. **Application tracking** - User application management system
6. **Interview prep** - Company-specific interview questions
7. **Visa timeline predictor** - H-1B approval timeline estimation

---

## 🙏 Credits

**Data Sources**:
- USCIS LCA Disclosure Data (H-1B)
- Fortune 500 company career pages
- Airtable job boards

**Technologies**:
- Snowflake Cortex AI
- dbt Labs
- Google Cloud Platform
- FastAPI
- Streamlit

---

**Document Version**: 1.0  
**Last Updated**: December 12, 2025  
**Maintained By**: Job Intelligence Platform Team
