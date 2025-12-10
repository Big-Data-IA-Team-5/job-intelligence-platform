# Backend Deployment Guide
## Job Intelligence Platform - Cloud Run

## 📋 Overview

This backend provides REST API endpoints for the Job Intelligence Platform, including:
- **Agent 1 (Search)** - Job search with semantic matching
- **Agent 2 (Chat)** - Intelligent Q&A with LLM-powered intent detection
- **Agent 3 (Classifier)** - Job classification and categorization
- **Agent 4 (Matcher)** - Resume-job matching
- **Analytics** - Job market insights and H-1B data analysis

---

## 🏗️ Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── routes/              # API endpoints
│   │   ├── chat.py          # Agent 2 chat endpoint
│   │   ├── search.py        # Agent 1 search endpoint
│   │   ├── classify.py      # Agent 3 classifier
│   │   ├── resume.py        # Agent 4 matcher
│   │   └── ...
│   └── models/              # Data models
├── snowflake/               # Snowflake agents (copied during build)
│   └── agents/
│       ├── agent1_search.py
│       ├── agent2_chat.py
│       ├── agent3_classifier.py
│       └── agent4_matcher.py
├── config/                  # Configuration files (copied during build)
├── Dockerfile               # Multi-stage production build
├── requirements.txt         # Python dependencies
├── build-and-push.sh        # Build & push to GCR
└── deploy-cloudrun.sh       # Deploy to Cloud Run
```

---

## 🔧 Prerequisites

### 1. Google Cloud Setup
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Login and set project
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 2. Store Secrets in Secret Manager
```bash
# Snowflake credentials
echo -n "YOUR_ACCOUNT" | gcloud secrets create snowflake-account --data-file=-
echo -n "YOUR_USER" | gcloud secrets create snowflake-user --data-file=-
echo -n "YOUR_PASSWORD" | gcloud secrets create snowflake-password --data-file=-
echo -n "YOUR_WAREHOUSE" | gcloud secrets create snowflake-warehouse --data-file=-
echo -n "YOUR_DATABASE" | gcloud secrets create snowflake-database --data-file=-
echo -n "YOUR_SCHEMA" | gcloud secrets create snowflake-schema --data-file=-
echo -n "YOUR_ROLE" | gcloud secrets create snowflake-role --data-file=-
```

---

## 🚀 Quick Deploy

### One-Command Deploy
```bash
# Set your project ID
export GCP_PROJECT_ID=your-project-id

# Build, push, and deploy
./build-and-push.sh && ./deploy-cloudrun.sh
```

---

## 📦 Manual Deployment

### Step 1: Build Docker Image
```bash
export GCP_PROJECT_ID=your-project-id
cd backend

# Build and push to GCR
./build-and-push.sh
```

**What it does:**
1. Copies `snowflake/agents/` into backend directory
2. Copies `config/` and `secrets.json` (for local testing)
3. Builds multi-stage Docker image (Python 3.11 slim)
4. Pushes to `gcr.io/PROJECT_ID/job-intelligence-backend:latest`
5. Cleans up temporary files

### Step 2: Deploy to Cloud Run
```bash
# Deploy with auto-scaling
./deploy-cloudrun.sh
```

**Configuration:**
- **Memory**: 2GB
- **CPU**: 2 vCPUs
- **Concurrency**: 80 requests per instance
- **Timeout**: 300 seconds (5 min)
- **Auto-scaling**: 1-10 instances
- **Port**: 8000

---

## 🔍 Verify Deployment

### Check Health
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe job-intelligence-backend \
    --region=us-central1 \
    --format="value(status.url)")

# Test health endpoint
curl $SERVICE_URL/health

# Expected response:
# {"status":"healthy","service":"Job Intelligence API"}
```

### Test API Endpoints
```bash
# View API docs
open $SERVICE_URL/docs

# Test Agent 2 (Chat)
curl -X POST $SERVICE_URL/api/chat/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me data engineer jobs in Boston",
    "user_id": "test-user"
  }'

# Test Agent 1 (Search)
curl -X POST $SERVICE_URL/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "software engineer",
    "location": "San Francisco",
    "limit": 10
  }'
```

---

## 📊 Monitoring

### View Logs
```bash
# Real-time logs
gcloud run logs tail job-intelligence-backend --region=us-central1

# Last 50 lines
gcloud run logs read job-intelligence-backend \
    --region=us-central1 \
    --limit=50
```

### Metrics in Cloud Console
```
https://console.cloud.google.com/run/detail/us-central1/job-intelligence-backend/metrics
```

Monitor:
- Request count and latency
- Error rate
- CPU and memory usage
- Instance count (auto-scaling)

---

## 🔄 Updates

### Deploy New Version
```bash
# 1. Make code changes
# 2. Build and push
./build-and-push.sh

# 3. Deploy (Cloud Run auto-updates)
./deploy-cloudrun.sh
```

### Rollback to Previous Version
```bash
gcloud run services update-traffic job-intelligence-backend \
    --to-revisions=PREVIOUS_REVISION=100 \
    --region=us-central1
```

---

## 🛠️ Local Development

### Run Locally
```bash
# Copy required files
cp -r ../snowflake ./
cp -r ../config ./
cp ../secrets.json ./

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn app.main:app --reload --port 8000

# Access API
open http://localhost:8000/docs
```

### Test with Docker Locally
```bash
# Build
docker build -t backend-local .

# Run
docker run -p 8000:8000 \
    -e SNOWFLAKE_ACCOUNT=your_account \
    -e SNOWFLAKE_USER=your_user \
    -e SNOWFLAKE_PASSWORD=your_password \
    backend-local
```

---

## 🔐 Security

### Environment Variables (Production)
Secrets are injected from Secret Manager:
- `SNOWFLAKE_ACCOUNT`
- `SNOWFLAKE_USER`
- `SNOWFLAKE_PASSWORD`
- `SNOWFLAKE_WAREHOUSE`
- `SNOWFLAKE_DATABASE`
- `SNOWFLAKE_SCHEMA`
- `SNOWFLAKE_ROLE`

### IAM Permissions Required
```bash
# Grant Cloud Run access to secrets
gcloud run services add-iam-policy-binding job-intelligence-backend \
    --region=us-central1 \
    --member="allUsers" \
    --role="roles/run.invoker"
```

---

## 💰 Cost Optimization

### Current Configuration
- **Estimated Cost**: $50-150/month (depending on traffic)
- **Free Tier**: 2 million requests/month, 360,000 GB-seconds

### Tips to Reduce Costs
1. **Adjust min instances**: Set `--min-instances=0` (cold starts)
2. **Reduce memory**: Use `--memory=1Gi` if sufficient
3. **Lower max instances**: Use `--max-instances=5` for testing
4. **Enable request timeout**: Current 5 min, reduce if possible

---

## 🐛 Troubleshooting

### Issue: Container fails to start
```bash
# Check build logs
gcloud builds list --limit=5

# Check detailed logs
gcloud run logs read job-intelligence-backend --limit=100
```

### Issue: Import errors for snowflake.agents
**Fix**: Ensure `build-and-push.sh` copied `snowflake/` directory correctly
```bash
# Verify in Dockerfile
COPY --chown=backend:backend ./snowflake ./snowflake
```

### Issue: Secrets not found
```bash
# List secrets
gcloud secrets list

# Verify secret values
gcloud secrets versions access latest --secret=snowflake-account
```

### Issue: High latency
- Increase CPU/memory
- Check Snowflake warehouse size
- Add caching layer (Redis)

---

## 📚 API Documentation

Once deployed, access interactive docs:
- **Swagger UI**: `https://YOUR_SERVICE_URL/docs`
- **ReDoc**: `https://YOUR_SERVICE_URL/redoc`

### Key Endpoints
- `GET /health` - Health check
- `POST /api/chat/ask` - Agent 2 chat
- `POST /api/search` - Agent 1 job search
- `POST /api/classify` - Agent 3 classification
- `POST /api/resume/match` - Agent 4 matching
- `GET /api/v1/analytics` - Analytics data

---

## 🔗 Related Services

- **Frontend**: Separate Streamlit deployment
- **Airflow**: Docker-based scheduler (not on Cloud Run)
- **Snowflake**: Data warehouse

---

## 📞 Support

Issues? Check:
1. Cloud Run logs: `gcloud run logs tail job-intelligence-backend`
2. Secret Manager: Verify all secrets exist
3. IAM permissions: Service account has required roles
4. Dockerfile: Build completes successfully

---

**Last Updated**: December 2025
