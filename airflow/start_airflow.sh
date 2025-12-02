#!/bin/bash
# Quick Start Airflow Script

export AIRFLOW_HOME=$(pwd)

echo "=========================================="
echo "🚀 Starting Airflow"
echo "=========================================="
echo ""
echo "Starting in standalone mode..."
echo "This will start both webserver and scheduler"
echo ""

airflow standalone
