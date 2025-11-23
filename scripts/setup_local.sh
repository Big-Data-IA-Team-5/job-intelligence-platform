#!/bin/bash

# Local Development Setup Script
# This script sets up the Job Intelligence Platform for local development

set -e

echo "🚀 Setting up Job Intelligence Platform..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup configuration files
echo "⚙️  Setting up configuration files..."

if [ ! -f config/.env ]; then
    cp config/.env.template config/.env
    echo "✅ Created config/.env - Please update with your credentials"
fi

if [ ! -f config/snowflake_config.yml ]; then
    cp config/snowflake_config.template config/snowflake_config.yml
    echo "✅ Created config/snowflake_config.yml - Please update with your credentials"
fi

if [ ! -f dbt/profiles.yml ]; then
    cp dbt/profiles.yml.template dbt/profiles.yml
    echo "✅ Created dbt/profiles.yml - Please update with your credentials"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p data
mkdir -p airflow/logs
mkdir -p dbt/target

# Install DBT dependencies
echo "🔧 Installing DBT dependencies..."
cd dbt
dbt deps || echo "⚠️  DBT deps failed - install DBT and configure profiles.yml"
cd ..

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update config/.env with your Snowflake credentials"
echo "2. Update config/snowflake_config.yml"
echo "3. Run Snowflake setup scripts in snowflake/setup/"
echo "4. Start services:"
echo "   - Backend: cd backend && uvicorn app.main:app --reload"
echo "   - Frontend: cd frontend && streamlit run Home.py"
echo "   - Airflow: cd airflow && docker-compose up"
