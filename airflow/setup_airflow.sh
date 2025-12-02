#!/bin/bash
# Airflow Local Setup and Test Script

set -e

echo "=========================================="
echo "🚀 Airflow Local Setup & Test"
echo "=========================================="

# Load secrets
SECRETS_FILE="../secrets.json"
if [ ! -f "$SECRETS_FILE" ]; then
    echo "❌ secrets.json not found!"
    exit 1
fi

# Export environment variables from secrets
export AIRFLOW_HOME=$(pwd)
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False

# Extract credentials from secrets.json
export SNOWFLAKE_USER=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['snowflake']['user'])")
export SNOWFLAKE_PASSWORD=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['snowflake']['password'])")
export SNOWFLAKE_ACCOUNT=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['snowflake']['account'])")
export SNOWFLAKE_WAREHOUSE=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['snowflake']['warehouse'])")
export SNOWFLAKE_DATABASE=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['snowflake']['database'])")
export SNOWFLAKE_SCHEMA=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['snowflake']['schema'])")

export AWS_ACCESS_KEY_ID=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['aws']['access_key_id'])")
export AWS_SECRET_ACCESS_KEY=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['aws']['secret_access_key'])")
export AWS_REGION=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['aws']['region'])")
export S3_BUCKET=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['aws']['s3_bucket'])")

export OPENAI_API_KEY=$(python3 -c "import json; print(json.load(open('$SECRETS_FILE'))['api']['openai_api_key'])")

echo "✓ Environment variables loaded from secrets.json"

# Check if Airflow is installed
if ! command -v airflow &> /dev/null; then
    echo ""
    echo "📦 Installing Apache Airflow..."
    pip3 install apache-airflow==2.7.3 --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.7.3/constraints-3.11.txt"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Initialize Airflow database
echo ""
echo "🗄️  Initializing Airflow database..."
airflow db init

# Create admin user
echo ""
echo "👤 Creating Airflow admin user..."
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "📋 Your DAGs:"
echo "   1. test_pipeline_dag (Test all pipelines)"
echo "   2. fortune500_scraper_dag (Daily at 1 AM UTC)"
echo "   3. airtable_scraper_dag (Daily at 6 AM UTC)"
echo "   4. h1b_loader_dag (Manual trigger)"
echo ""
echo "🚀 To start Airflow:"
echo "   Terminal 1: airflow webserver --port 8080"
echo "   Terminal 2: airflow scheduler"
echo ""
echo "🌐 Access Airflow UI:"
echo "   URL: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "🧪 To test the pipeline:"
echo "   1. Go to http://localhost:8080"
echo "   2. Find 'test_pipeline_dag'"
echo "   3. Click the play button to trigger"
echo ""
