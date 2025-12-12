# Job Intelligence Platform - Complete Demo Guide

## 🎯 Problem Statement

**The Challenge:**  
International students and recent graduates face enormous friction when searching for visa-friendly jobs. They must:
- Manually check if companies sponsor H-1B visas
- Sift through thousands of irrelevant postings
- Research employer approval rates from scattered government data
- Tailor resumes without knowing what skills matter most

**Our Solution:**  
A unified AI-powered platform that aggregates 80K+ jobs, enriches them with real H-1B sponsorship data, and delivers personalized recommendations through natural language conversation.

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  📋 Airtable Boards    │  🏢 Fortune 500 Sites   │  📊 USCIS H-1B Data     │
│  (Graduate Jobs)       │  (Company Careers)      │  (LCA Disclosure)       │
└────────────┬───────────┴────────────┬────────────┴────────────┬────────────┘
             │                        │                         │
             ▼                        ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AIRFLOW (Cloud Composer)                            │
│  dag_airtable_grad_scraper.py  │  dag_fortune500_scraper.py  │  dag_h1b... │
│  dag_internship_scraper.py     │  dag_embedding_generator.py │             │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SNOWFLAKE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  RAW Schema           │  STAGING Schema        │  PROCESSED Schema         │
│  └─ JOBS_RAW (80K+)   │  └─ stg_jobs          │  └─ JOBS_PROCESSED (47K)  │
│  └─ H1B_LCA_DATA      │  └─ dedup_jobs        │  └─ EMPLOYER_INTELLIGENCE │
│                       │                        │  └─ EMBEDDED_JOBS         │
├─────────────────────────────────────────────────────────────────────────────┤
│  DBT Models: stg_jobs → dedup_jobs → h1b_matched_jobs → classified_jobs    │
│              → embedded_jobs (Cortex EMBED_TEXT_768)                       │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND (Cloud Run)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/v1/analytics/*   │  /api/v1/jobs/*     │  /api/v1/recommendations/*  │
│  /api/v1/chat/*        │  /api/v1/resume/*   │  /api/v1/search/*           │
├─────────────────────────────────────────────────────────────────────────────┤
│  AI AGENTS:                                                                 │
│  • Agent 1: SQL Generator (Mistral-Large via Cortex)                       │
│  • Agent 2: Chat Intelligence (GPT-4 + Cortex Complete)                    │
│  • Agent 3: Job Classifier (Cortex Complete)                               │
│  • Agent 4: Resume Matcher (Embedding Similarity)                          │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STREAMLIT FRONTEND (Cloud Run)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Home.py (Chat Interface)  │  1_📊_Advanced_Analytics.py  │  2_💼_Jobs_DB  │
│  - Natural language search │  - Company insights          │  - Filtered    │
│  - Resume upload/analyze   │  - H-1B sponsor rankings     │    job table   │
│  - Conversation context    │  - Salary trends             │  - Apply links │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📱 Frontend Pages - What You'll See

### **Page 1: Home.py (AI Chat Interface)**
**URL:** `https://job-intelligence-frontend-97083220044.us-central1.run.app`

| Feature | What to Demo | Sample Query |
|---------|-------------|--------------|
| Natural Language Search | Type questions like a real conversation | "Find me data engineer jobs in NYC that sponsor H-1B" |
| Resume Upload | Click 📎 to upload PDF/DOCX | Upload any resume to enable personalized matching |
| Context Awareness | Ask follow-ups without repeating yourself | "What about remote ones?" (after previous search) |
| Job Matching | After uploading resume | "Match my resume to the best jobs" |
| Company Research | Ask about specific employers | "Tell me about Google's H-1B approval rate" |

**Key Code:** `frontend/Home.py`, `frontend/utils/context_manager.py`

---

### **Page 2: Advanced Analytics Dashboard**
**URL:** `/1_📊_Advanced_Analytics`

| Visualization | Data Shown | Insight |
|---------------|-----------|---------|
| Summary Cards | Total jobs, companies, H-1B sponsors, 7-day new | Platform scale at a glance |
| Top Companies Chart | Companies ranked by job count | See who's hiring most |
| H-1B Sponsor Table | Sponsors with approval rates, total filed, certified | **Key differentiator** - real government data |
| Location Heatmap | Jobs by city/state | Geographic job distribution |
| Salary by Role | Avg salary per job category | Compensation benchmarks |

**Key Code:** `frontend/pages/1_📊_Advanced_Analytics.py`  
**Backend Endpoints:** `/api/v1/analytics/summary`, `/api/v1/analytics/visa-sponsors`, `/api/v1/analytics/companies`

---

### **Page 3: Jobs Database**
**URL:** `/2_💼_Jobs_Database`

| Filter | Options | Purpose |
|--------|---------|---------|
| Keyword Search | Any text | Match title/description |
| Location | City/state dropdown | Geographic filter |
| H-1B Sponsor Only | Toggle | Show only visa-friendly jobs |
| Remote/Hybrid/Onsite | Dropdown | Work model preference |
| Salary Range | Min-Max slider | Compensation filter |

**Features:**
- Paginated results with "NEW" and "HOT" badges
- Direct "Apply" links to original postings
- Company cards with H-1B approval rates inline

**Key Code:** `frontend/pages/2_💼_Jobs_Database.py`  
**Backend Endpoint:** `/api/v1/jobs/search`

---

## 🤖 AI Agents - Behind the Scenes

### **Agent 1: SQL Generator**
- **Purpose:** Converts natural language to Snowflake SQL
- **Model:** Mistral-Large via Snowflake Cortex
- **Code:** `backend/snowflake/agents/agent1_search.py`
- **Demo Query:** "Show me senior data scientist jobs paying over $150K in San Francisco"

### **Agent 2: Chat Intelligence**
- **Purpose:** Orchestrates conversation, retrieves data, formats responses
- **Features:** Conversation state, follow-up handling, distributed caching
- **Code:** `backend/snowflake/agents/agent2_chat.py` (1,880 lines)
- **Demo:** Multi-turn conversation with context retention

### **Agent 3: Job Classifier**
- **Purpose:** Categorizes jobs (Engineering, Data, Product, etc.)
- **Model:** Cortex Complete (Mistral)
- **Code:** `backend/snowflake/agents/agent3_classifier.py`

### **Agent 4: Resume Matcher**
- **Purpose:** Matches uploaded resumes to jobs using embeddings
- **Tech:** OpenAI embeddings + cosine similarity
- **Code:** `backend/snowflake/agents/agent4_matcher.py`, `backend/app/routes/agent4_matcher.py`
- **Demo:** Upload resume → "Find jobs that match my skills"

---

## 🔄 Data Pipeline - Airflow DAGs

| DAG | Schedule | What It Does |
|-----|----------|--------------|
| `dag_airtable_grad_scraper` | Daily 6 AM EST | Scrapes graduate job boards via Selenium |
| `dag_fortune500_scraper` | Weekly | Scrapes Fortune 500 company career pages |
| `dag_internship_scraper` | Daily | Scrapes internship-specific boards |
| `dag_h1b_loader` | Monthly | Loads USCIS LCA disclosure data |
| `dag_embedding_generator` | Daily 7 AM EST | Generates Cortex embeddings for new jobs |
| `dag_dbt_transformations` | After scrapers | Runs DBT models to transform data |

**Key Code:** `airflow/dags/`, `scripts/generate_embeddings.py`

---

## 🔍 Sample Demo Queries

### Basic Job Search
```
"Find software engineer jobs in Boston"
"Show me remote data analyst positions"
"What entry-level jobs are available at Microsoft?"
```

### H-1B Focused
```
"Which companies have the highest H-1B approval rates?"
"Find machine learning jobs that sponsor visas"
"Compare H-1B sponsorship at Google vs Amazon"
```

### Resume Matching (after upload)
```
"What jobs match my resume?"
"How can I improve my resume for data science roles?"
"Which skills am I missing for senior positions?"
```

### Analytics Questions
```
"What's the average salary for product managers?"
"Which cities have the most tech jobs?"
"Show me job posting trends over the last month"
```

---

## 📊 Key Metrics to Highlight

| Metric | Current Value | Source |
|--------|---------------|--------|
| Total Jobs Indexed | 80,000+ | `RAW.JOBS_RAW` |
| Processed Jobs | 47,000+ | `PROCESSED.JOBS_PROCESSED` |
| H-1B Sponsor Companies | 2,500+ | `EMPLOYER_INTELLIGENCE` |
| LCA Records | 200,000+ | `H1B_LCA_DATA` |
| Daily New Jobs | 500-1,000 | Scrapers |

---

## 🛠️ Technical Differentiators

1. **Snowflake Cortex Integration**
   - `EMBED_TEXT_768` for semantic search embeddings
   - `CORTEX.COMPLETE` for LLM-powered classification
   - Native vector similarity without external APIs

2. **Real H-1B Government Data**
   - USCIS LCA Disclosure files (official source)
   - Employer-level approval rates calculated from actual filings
   - Not scraped from third-party sites

3. **Conversation Context Manager**
   - Tracks entities across turns (job title, location, company)
   - Enables natural follow-up questions
   - Code: `frontend/utils/context_manager.py`

4. **Multi-Agent Architecture**
   - Specialized agents for different tasks
   - Automatic fallback between agents
   - Telemetry tracking for optimization

---

## 🌐 Live URLs

| Service | URL |
|---------|-----|
| Frontend | https://job-intelligence-frontend-97083220044.us-central1.run.app |
| Backend API | https://job-intelligence-backend-97083220044.us-central1.run.app |
| API Docs | https://job-intelligence-backend-97083220044.us-central1.run.app/docs |
| Airflow | Cloud Composer Console → `job-intel-airflow` |

---

## ✅ Pre-Demo Checklist

- [ ] Backend Cloud Run service is running (check `/health` endpoint)
- [ ] Frontend loads without errors
- [ ] Recent Airflow DAG runs succeeded (embedding_generator)
- [ ] Snowflake warehouse is resumed
- [ ] Sample resume PDF ready for upload demo
- [ ] Test queries work: "Find data engineer jobs in NYC"

---

## 🚨 Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| "Unable to connect to backend" | Backend service down | Redeploy backend to Cloud Run |
| Empty job results | Snowflake connection failed | Check `secrets.json` credentials |
| Embeddings not syncing | DAG error | Check Airflow logs, re-upload `generate_embeddings.py` |
| Slow responses | Cold start | First request warms up; subsequent faster |
| Resume upload fails | File too large | Limit to 5MB PDFs |

---

## 📁 Quick File Reference

| Purpose | Path |
|---------|------|
| Main chat interface | `frontend/Home.py` |
| Analytics dashboard | `frontend/pages/1_📊_Advanced_Analytics.py` |
| Jobs database | `frontend/pages/2_💼_Jobs_Database.py` |
| API routes | `backend/app/routes/*.py` |
| AI agents | `backend/snowflake/agents/*.py` |
| DBT models | `dbt/models/staging/`, `dbt/models/processing/` |
| Scrapers | `scrapers/*.py` |
| Airflow DAGs | `airflow/dags/*.py` |
| Embedding generator | `scripts/generate_embeddings.py` |

---

*Last Updated: December 12, 2025*
