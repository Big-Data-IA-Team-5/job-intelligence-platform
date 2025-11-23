#!/usr/bin/env python3
"""
Create .env file from secrets.json
Everyone runs this after getting secrets.json
"""
import json
import os

def create_env_file():
    # Check if secrets.json exists
    if not os.path.exists('secrets.json'):
        print("❌ Error: secrets.json not found!")
        print("📥 Download secrets.json from team Slack first")
        return
    
    # Load secrets
    with open('secrets.json', 'r') as f:
        secrets = json.load(f)
    
    # Generate .env content
    env_content = f"""# Job Intelligence Platform - Environment Variables
# Generated from secrets.json on {secrets['generated_at']}
# DO NOT COMMIT THIS FILE!

# ===========================================
# Snowflake Configuration
# ===========================================
SNOWFLAKE_ACCOUNT={secrets['snowflake']['account']}
SNOWFLAKE_USER={secrets['snowflake']['user']}
SNOWFLAKE_PASSWORD={secrets['snowflake']['password']}
SNOWFLAKE_DATABASE={secrets['snowflake']['database']}
SNOWFLAKE_WAREHOUSE={secrets['snowflake']['warehouse']}
SNOWFLAKE_SCHEMA={secrets['snowflake']['schema']}
SNOWFLAKE_ROLE={secrets['snowflake']['role']}

# ===========================================
# AWS S3 Configuration
# ===========================================
AWS_ACCESS_KEY_ID={secrets['aws']['access_key_id']}
AWS_SECRET_ACCESS_KEY={secrets['aws']['secret_access_key']}
AWS_S3_BUCKET={secrets['aws']['s3_bucket']}
AWS_REGION={secrets['aws']['region']}

# ===========================================
# API Configuration
# ===========================================
API_SECRET_KEY={secrets['api']['secret_key']}
OPENAI_API_KEY={secrets['api']['openai_api_key']}
API_HOST=0.0.0.0
API_PORT=8080

# ===========================================
# Airflow Configuration
# ===========================================
AIRFLOW_HOME=/opt/airflow
AIRFLOW__CORE__FERNET_KEY={secrets['airflow']['fernet_key']}
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__WEBSERVER__SECRET_KEY={secrets['api']['secret_key']}
_AIRFLOW_WWW_USER_USERNAME={secrets['airflow']['admin_username']}
_AIRFLOW_WWW_USER_PASSWORD={secrets['airflow']['admin_password']}

# ===========================================
# Environment
# ===========================================
ENVIRONMENT={secrets['environment']}
"""
    
    # Write to config/.env
    os.makedirs('config', exist_ok=True)
    with open('config/.env', 'w') as f:
        f.write(env_content)
    
    print("✅ config/.env created successfully!")
    print(f"📍 Location: {os.path.abspath('config/.env')}")
    print("\n⚠️  This file contains secrets - DO NOT COMMIT!")
    print("\n🔍 Verify with: cat config/.env")

if __name__ == "__main__":
    create_env_file()