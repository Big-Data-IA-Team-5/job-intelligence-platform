# Job Intelligence Platform Demo Guide

## Purpose
This guide equips demo presenters with a concise story, environment checklist, and callouts inside the codebase. It explains what problem we solve, how the system is structured, and where to find supporting artifacts during live walkthroughs.

## Problem Statement
Graduates and international candidates struggle to discover visa-friendly roles that match their skills. Companies likewise cannot surface high-signal applicants quickly. The platform unifies scraped labor-market data, Snowflake analytics, and AI-driven search to produce job recommendations, resume insights, and visa-readiness intelligence.

## Core Value Proposition
1. **Unified Job Intelligence** – Normalizes 80K+ postings, deduplicates them, and enriches attributes (salary bands, categories, H-1B metadata).
2. **AI Agents for Guidance** – Multiple FastAPI agents assist with search, chat-style Q&A, resume improvement, and job matching.
3. **Continuous Data Refresh** – Airflow DAGs scrape, process, embed, and publish new roles every few hours.

## Demo Narrative
1. **Set the stage** – Highlight the pain points for students and talent teams (visa uncertainty, noisy job boards, manual research).
2. **Architecture slide** – Reference docs/architecture.md for the full diagram covering Scrapers → Airflow → Snowflake → FastAPI → Streamlit.
3. **Show the product**
   - Frontend (Streamlit): rich search, saved jobs, resume analyzer.
   - Backend API: FastAPI docs from the deployed Cloud Run URL.
   - Analytics console: jobs summary and insights endpoints.
4. **Go deeper on intelligence** – Point to Snowflake Cortex usage (dbt/models/processing/embedded_jobs.sql) and agent logic (backend/app/routes/agent2_chat.py).
5. **Close with outcomes** – Faster job discovery, higher visa-sponsor coverage, actionable resume feedback.

## Environment Checklist
- **Frontend**: Streamlit app deployed to Cloud Run (`job-intelligence-frontend`). Requires BACKEND_URL and APP_TIMEZONE env vars.
- **Backend**: FastAPI app deployed to Cloud Run (`job-intelligence-backend`). Depends on secrets.json for Snowflake credentials.
- **Airflow (Composer)**: DAG `embedding_generator` keeps embeddings fresh; ensure latest scripts uploaded to `gs://us-central1-job-intel-airfl-273e51fd-bucket`.
- **Snowflake**: Databases JOB_INTELLIGENCE.RAW/PROCESSED/PROCESSING with warehouse sized for nightly refresh.
- **Monitoring**: Cloud Logging for DAG traces, Cloud Run logs for API/front.

## Key Repositories & Entry Points
- **Scrapers**: scrapers/*.py – ingest from Airtable, Fortune 500, internships.
- **ETL & Analytics**: dbt/models – deduplication, classification, embedding generation.
- **APIs**: backend/app/routes – agents, analytics, recommendations, resume matching.
- **Utilities**: backend/app/utils – Snowflake connector, validators, agent manager.
- **Airflow DAGs**: airflow/airflow/dags – orchestrate scraping and embedding pipelines.
- **Frontend**: frontend/pages, frontend/utils – Streamlit pages and shared helpers.

## Demo Flow Cheat Sheet
| Step | Goal | Callout |
| --- | --- | --- |
| 1 | Landing page | Mention Streamlit `Home.py` running on Cloud Run. |
| 2 | Search jobs | Agent-backed endpoint `backend/app/routes/jobs.py`. |
| 3 | Resume insights | `backend/app/routes/resume.py`, highlight AI scoring logic. |
| 4 | Analytics overview | `backend/app/routes/analytics.py` hitting Snowflake summaries. |
| 5 | Behind the scenes | Show Airflow logs & `scripts/generate_embeddings.py` merge strategy. |

## Data Flow Summary
1. Scrapers download raw postings into Snowflake RAW tables.
2. dbt transformations cleanse, classify, deduplicate, and produce embeddings via Cortex.
3. FastAPI exposes REST endpoints consumed by the Streamlit UI.
4. Airflow periodically triggers updates to keep recommendations current.

## Pre-Demo Sanity Checks
- Latest code deployed to Cloud Run (frontend/backend).
- Airflow DAG `embedding_generator` succeeded within the last 24 hours.
- Snowflake warehouse is resumed and credentials valid.
- Streamlit environment variables set (BACKEND_URL, APP_TIMEZONE).
- secrets.json contains up-to-date API keys (OpenAI/Cortex credentials).

## Troubleshooting Quick Wins
- **API 500 errors**: check backend logs, validate Snowflake connectivity.
- **Missing embeddings**: ensure `gsutil cp scripts/generate_embeddings.py <bucket>/data/scripts/` executed after changes.
- **Slow queries**: scale Snowflake warehouse or limit job batch sizes in scripts.
- **Authorization failures**: refresh GCP service account keys referenced in secrets.json.

## Next Steps & Differentiators
- Expand to additional visa types (TN, O-1).
- Add candidate tracking dashboards for universities/employers.
- Integrate resume parsing with multi-lingual support.
- Machine learning scoring for job-person fit beyond embeddings.

**Reminder:** keep the story outcomes-driven—focus on how the platform reduces time-to-offer for international students while giving recruiters higher-quality pipelines.
