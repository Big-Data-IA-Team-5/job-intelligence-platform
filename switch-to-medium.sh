#!/bin/bash

echo "🔍 Monitoring Composer environment creation..."
echo "Started at: $(date)"
echo ""

while true; do
  STATE=$(gcloud composer environments describe job-intel-airflow --location=us-central1 --format="value(state)" 2>/dev/null)
  
  if [ "$STATE" = "RUNNING" ]; then
    echo ""
    echo "✅ Large environment is RUNNING at $(date)"
    echo "🗑️  Deleting Large environment..."
    gcloud composer environments delete job-intel-airflow --location=us-central1 --quiet
    
    echo ""
    echo "⏳ Waiting for deletion to complete..."
    sleep 60
    
    echo "🚀 Creating MEDIUM environment with 4 CPU/16GB RAM..."
    gcloud composer environments create job-intel-airflow \
        --location=us-central1 \
        --image-version=composer-2.16.0-airflow-2.9.3 \
        --service-account=composer-airflow@job-intelligence-platform.iam.gserviceaccount.com \
        --environment-size=medium \
        --scheduler-count=2 \
        --scheduler-cpu=4 \
        --scheduler-memory=8 \
        --scheduler-storage=5 \
        --web-server-cpu=2 \
        --web-server-memory=4 \
        --web-server-storage=5 \
        --worker-cpu=4 \
        --worker-memory=16 \
        --worker-storage=10 \
        --min-workers=2 \
        --max-workers=10 \
        --airflow-configs=core-parallelism=64,core-max_active_tasks_per_dag=32
    
    echo ""
    echo "✅ Medium environment creation started!"
    break
    
  elif [ "$STATE" = "ERROR" ]; then
    echo "❌ Large environment creation FAILED at $(date)"
    echo "🚀 Creating MEDIUM environment instead..."
    gcloud composer environments create job-intel-airflow \
        --location=us-central1 \
        --image-version=composer-2.16.0-airflow-2.9.3 \
        --service-account=composer-airflow@job-intelligence-platform.iam.gserviceaccount.com \
        --environment-size=medium \
        --scheduler-count=2 \
        --scheduler-cpu=4 \
        --scheduler-memory=8 \
        --scheduler-storage=5 \
        --web-server-cpu=2 \
        --web-server-memory=4 \
        --web-server-storage=5 \
        --worker-cpu=4 \
        --worker-memory=16 \
        --worker-storage=10 \
        --min-workers=2 \
        --max-workers=10 \
        --airflow-configs=core-parallelism=64,core-max_active_tasks_per_dag=32
    break
    
  else
    echo "⏳ $(date) - State: $STATE (checking again in 60 seconds...)"
    sleep 60
  fi
done

echo ""
echo "🎯 Script completed at $(date)"
