"""
FastAPI Configuration
Loads environment variables and settings
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parents[2] / 'config' / '.env'
load_dotenv(env_path)

class Settings:
    # App Info
    APP_NAME = "Job Intelligence Platform API"
    VERSION = "1.0.0"
    DESCRIPTION = "AI-powered job search platform for international students"
    
    # Server
    HOST = "0.0.0.0"
    PORT = 8000
    
    # Snowflake Connection
    SNOWFLAKE_ACCOUNT = os.getenv('SNOWFLAKE_ACCOUNT')
    SNOWFLAKE_USER = os.getenv('SNOWFLAKE_USER')
    SNOWFLAKE_PASSWORD = os.getenv('SNOWFLAKE_PASSWORD')
    SNOWFLAKE_DATABASE = os.getenv('SNOWFLAKE_DATABASE', 'job_intelligence')
    SNOWFLAKE_WAREHOUSE = os.getenv('SNOWFLAKE_WAREHOUSE', 'compute_wh')
    SNOWFLAKE_SCHEMA = os.getenv('SNOWFLAKE_SCHEMA', 'processed')
    SNOWFLAKE_ROLE = os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
    
    # Agent Paths
    AGENT_BASE_PATH = Path(__file__).parents[2] / 'snowflake' / 'agents'
    
    # CORS
    CORS_ORIGINS = [
        "http://localhost:8501",  # Streamlit
        "http://localhost:3000",  # React (if needed)
    ]
    
    # Limits
    MAX_SEARCH_RESULTS = 100
    MAX_RESUME_SIZE_MB = 5

settings = Settings()