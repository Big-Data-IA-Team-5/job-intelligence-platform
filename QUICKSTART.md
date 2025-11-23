# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- Snowflake Account
- Git

### Step 1: Clone & Setup
```bash
git clone <repo-url>
cd job-intelligence-platform
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh
```

### Step 2: Configure Snowflake
```bash
# Copy and edit config files
cp config/.env.template config/.env
cp config/snowflake_config.template config/snowflake_config.yml

# Edit with your Snowflake credentials
nano config/snowflake_config.yml
```

### Step 3: Initialize Database
```bash
# Run Snowflake setup scripts (use SnowSQL or Snowflake UI)
# Execute files in snowflake/setup/ in order:
# - 01_database_setup.sql
# - 02_schemas.sql
# - 03_raw_tables.sql
# - 04_processed_tables.sql
# - 05_user_tables.sql
```

### Step 4: Start Services
```bash
docker-compose up -d
```

### Step 5: Access Applications
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000/docs
- **Airflow**: http://localhost:8080 (admin/admin)

## 📦 What's Included

✅ **52+ Files** across complete project structure
✅ Job scraping from Indeed & other sources
✅ Snowflake data warehouse setup
✅ DBT data transformation pipelines
✅ FastAPI REST API backend
✅ Streamlit web interface
✅ Apache Airflow orchestration
✅ H1B visa sponsorship matching
✅ AI-powered semantic search
✅ Resume-to-job matching
✅ Analytics dashboard
✅ Docker containerization
✅ CI/CD with GitHub Actions

## 🎯 Key Features

- **Semantic Job Search**: Find jobs using natural language
- **Resume Matching**: AI matches your resume to best jobs
- **H1B Sponsorship Data**: See which companies sponsor visas
- **Market Analytics**: Insights into trends and companies
- **Remote Jobs**: Filter for remote opportunities

## 📚 Documentation

- Architecture: `docs/architecture.md`
- API Docs: `docs/api_documentation.md`
- Deployment: `docs/deployment_guide.md`

## 🔧 Development

Run individual services:

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
pip install -r requirements.txt
streamlit run Home.py
```

**Airflow:**
```bash
cd airflow
docker-compose up
```

## 🐛 Troubleshooting

**Can't connect to Snowflake?**
- Verify credentials in `config/snowflake_config.yml`
- Check network connectivity
- Ensure warehouse is running

**Docker issues?**
- Restart Docker daemon
- Try `docker-compose down && docker-compose up`

**DBT errors?**
- Configure `dbt/profiles.yml`
- Run `dbt debug` to test connection

## 📞 Support

Open an issue on GitHub or check the documentation.

---

**Ready to go?** Run `docker-compose up -d` and visit http://localhost:8501
