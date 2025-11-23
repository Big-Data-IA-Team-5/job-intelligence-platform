"""
Load H1B Data Script
Downloads and loads H1B visa data into Snowflake
"""
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import os
import yaml
import requests
from io import StringIO


def get_snowflake_connection(config_path='config/snowflake_config.yml'):
    """Create Snowflake connection"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return snowflake.connector.connect(
        account=config['account'],
        user=config['user'],
        password=config['password'],
        warehouse=config['warehouse'],
        database=config['database'],
        role=config.get('role', 'ACCOUNTADMIN')
    )


def download_h1b_data(year=2023):
    """
    Download H1B data from USCIS or use sample data
    Note: Actual URL would need to be updated with real source
    """
    print(f"📥 Downloading H1B data for {year}...")
    
    # This is a placeholder - replace with actual data source
    # Real data: https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub
    
    # For now, create sample data
    sample_data = {
        'case_number': [f'I-200-{i:05d}' for i in range(1000)],
        'case_status': ['Certified'] * 1000,
        'employer_name': ['Google', 'Microsoft', 'Amazon', 'Meta', 'Apple'] * 200,
        'job_title': ['Software Engineer', 'Data Scientist', 'ML Engineer'] * 333 + ['Product Manager'],
        'soc_code': ['15-1252'] * 1000,
        'soc_title': ['Software Developers'] * 1000,
        'worksite_city': ['San Francisco', 'Seattle', 'New York'] * 333 + ['Austin'],
        'worksite_state': ['CA', 'WA', 'NY'] * 333 + ['TX'],
        'prevailing_wage': [120000, 130000, 140000, 150000, 160000] * 200,
        'wage_unit': ['Year'] * 1000,
        'fiscal_year': [year] * 1000,
        'received_date': [f'{year}-01-15'] * 1000,
        'decision_date': [f'{year}-03-15'] * 1000
    }
    
    df = pd.DataFrame(sample_data)
    print(f"✅ Loaded {len(df)} H1B records")
    
    return df


def load_to_snowflake(df, conn):
    """Load DataFrame to Snowflake"""
    print("📤 Loading data to Snowflake...")
    
    try:
        cursor = conn.cursor()
        
        # Use RAW schema
        cursor.execute("USE SCHEMA RAW")
        
        # Write data
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name='H1B_DATA',
            database='JOB_INTELLIGENCE',
            schema='RAW',
            auto_create_table=False,
            overwrite=False
        )
        
        if success:
            print(f"✅ Successfully loaded {nrows} rows to Snowflake")
            return nrows
        else:
            print("❌ Failed to load data")
            return 0
            
    except Exception as e:
        print(f"❌ Error loading data: {str(e)}")
        raise
    finally:
        cursor.close()


def main():
    """Main execution"""
    print("🚀 Starting H1B data load process...")
    
    # Download data
    df = download_h1b_data(2023)
    
    # Connect to Snowflake
    print("🔌 Connecting to Snowflake...")
    conn = get_snowflake_connection()
    
    try:
        # Load data
        rows_loaded = load_to_snowflake(df, conn)
        
        print(f"\n✅ Process complete! Loaded {rows_loaded} H1B records")
        
    finally:
        conn.close()
        print("🔌 Connection closed")


if __name__ == "__main__":
    main()
