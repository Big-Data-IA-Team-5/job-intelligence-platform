"""
Load H-1B FY2025 Q3 Data - ALL 97 fields
Loads complete H-1B disclosure data from CSV into Snowflake
"""
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from datetime import datetime
import json
import sys


def load_secrets():
    """Load secrets from secrets.json"""
    with open('secrets.json', 'r') as f:
        return json.load(f)


def get_snowflake_connection():
    """Get Snowflake connection from secrets.json"""
    secrets = load_secrets()
    sf_config = secrets['snowflake']
    
    return snowflake.connector.connect(
        user=sf_config['user'],
        password=sf_config['password'],
        account=sf_config['account'],
        warehouse=sf_config['warehouse'],
        database=sf_config['database'],
        schema=sf_config['schema'],
        role=sf_config['role']
    )


def load_h1b_full_data(csv_path: str):
    """Load complete H-1B data with all 97 fields."""
    
    print("=" * 80)
    print(f"📂 Loading H-1B CSV: {csv_path}")
    print("=" * 80)
    
    # Read CSV with all 97 columns
    print("\n📊 Reading CSV file...")
    df = pd.read_csv(csv_path, low_memory=False)
    
    print(f"✅ Loaded {len(df):,} records with {len(df.columns)} columns")
    print(f"\nColumns: {', '.join(df.columns[:10])}... and {len(df.columns) - 10} more")
    
    # Clean column names (lowercase, underscore)
    df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')
    
    # Convert date columns - FIX for Snowflake
    print("\n🔄 Converting date columns...")
    date_columns = ['received_date', 'decision_date', 'original_cert_date', 
                   'begin_date', 'end_date']
    for col in date_columns:
        if col in df.columns:
            # Convert to datetime then to string format Snowflake likes
            df[col] = pd.to_datetime(df[col], errors='coerce')
            df[col] = df[col].dt.strftime('%Y-%m-%d')
            # Replace NaT with None
            df[col] = df[col].replace('NaT', None)
    
    # Convert numeric columns
    print("🔄 Converting numeric columns...")
    numeric_columns = ['wage_rate_of_pay_from', 'wage_rate_of_pay_to', 
                      'prevailing_wage', 'total_worker_positions', 
                      'worksite_workers', 'total_worksite_locations']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Add loaded_at timestamp
    df['loaded_at'] = datetime.now()
    
    # Connect to Snowflake
    print("\n🔌 Connecting to Snowflake...")
    conn = get_snowflake_connection()
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("USE DATABASE job_intelligence")
        cursor.execute("USE SCHEMA raw")
        
        # Clear old data
        print("🗑️ Truncating existing H-1B data...")
        cursor.execute("TRUNCATE TABLE h1b_raw")
        
        # Load data using write_pandas (handles all columns automatically!)
        print(f"\n📥 Uploading {len(df):,} records with ALL {len(df.columns)} columns to Snowflake...")
        print("⏱️  This may take 5-15 minutes for 100K+ records...")
        
        success, nchunks, nrows, _ = write_pandas(
            conn=conn,
            df=df,
            table_name='H1B_RAW',
            database='JOB_INTELLIGENCE',
            schema='RAW',
            chunk_size=5000,
            auto_create_table=False,  # Table already exists with all 98 columns
            quote_identifiers=False  # Don't quote table names
        )
        
        if success:
            print(f"\n✅ Successfully loaded {nrows:,} records in {nchunks} chunks!")
        else:
            print("\n❌ Load failed")
            return
        
        # Verify
        print("\n🔍 Verifying data...")
        cursor.execute("SELECT COUNT(*) FROM raw.h1b_raw")
        count = cursor.fetchone()[0]
        print(f"✓ Database contains {count:,} records")
        
        # Show sample with contact info
        print("\n📧 Sample records with contact information:")
        cursor.execute("""
            SELECT 
                employer_name,
                job_title,
                employer_poc_email,
                agent_attorney_email_address,
                lawfirm_name_business_name,
                wage_rate_of_pay_from,
                case_status
            FROM raw.h1b_raw
            WHERE employer_poc_email IS NOT NULL
               OR agent_attorney_email_address IS NOT NULL
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            print(f"\n  Company: {row[0]}")
            print(f"  Title: {row[1]}")
            if row[2]:
                print(f"  POC Email: {row[2]}")
            if row[3]:
                print(f"  Attorney Email: {row[3]}")
            if row[4]:
                print(f"  Law Firm: {row[4]}")
            print(f"  Wage: ${row[5]:,.0f} | Status: {row[6]}")
        
        # Statistics
        print("\n📊 Status Distribution:")
        cursor.execute("""
            SELECT 
                case_status,
                COUNT(*) as count,
                COUNT(employer_poc_email) as has_poc_email,
                COUNT(agent_attorney_email_address) as has_attorney_email
            FROM raw.h1b_raw
            GROUP BY case_status
            ORDER BY count DESC
        """)
        
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]:,} ({row[2]:,} POC emails, {row[3]:,} attorney emails)")
        
    finally:
        cursor.close()
        conn.close()
    
    print("\n" + "=" * 80)
    print("✅ H-1B FULL DATA LOADING COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/load_h1b_data.py data/LCA_Disclosure_Data_FY2025_Q3.csv")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    load_h1b_full_data(csv_path)
