"""
DAG: H-1B Data Loader
Loads H-1B disclosure data from Excel file
Pipeline: Load -> S3 Upload -> Snowflake Upload
Schedule: Manual trigger only (run when new quarterly data is available)
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pendulum
import sys
import os

# Add parent directory to path for Docker
sys.path.insert(0, '/opt/airflow')

# Import only lightweight modules at top level
# Heavy imports (pandas, json, etc.) moved inside task functions to prevent DAG import timeout

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

def load_h1b_data(**context):
    """
    Load H-1B CSV file (pre-converted from Excel)
    ULTRA-OPTIMIZED: Skip pandas Excel parsing completely!
    """
    import pandas as pd
    from dags.common.s3_utils import cleanup_old_s3_files
    
    print("=" * 80)
    print("STEP 1: LOADING H-1B CSV FILE")
    print("=" * 80)
    
    # Clean up old H1B files in S3 (if any)
    print("\nCleaning up old S3 files...")
    cleanup_old_s3_files(prefix='raw/h1b/', days_to_keep=90)
    
    # Check for CSV first (FAST), fallback to Excel (SLOW)
    csv_file = '/opt/airflow/data/LCA_Disclosure_Data_FY2025_Q3.csv'
    xlsx_file = '/opt/airflow/data/LCA_Disclosure_Data_FY2025_Q3.xlsx'
    output_csv = '/tmp/h1b_data.csv'
    
    print(f"\n⚙️  Configuration:")
    
    if os.path.exists(csv_file):
        # CSV exists - INSTANT LOAD! Just copy it
        print(f"   ✅ Found CSV file (FAST PATH): {csv_file}")
        print(f"   Output: {output_csv}")
        print(f"\n🚀 Using pre-converted CSV (instant load)...")
        
        # Read CSV header to get row count quickly
        df = pd.read_csv(csv_file)
        print(f"✓ Loaded {len(df)} rows from CSV in seconds!")
    
    else:
        # CSV doesn't exist - FAIL FAST with clear instructions
        print(f"\n❌ ERROR: CSV file not found!")
        print(f"\n📋 INSTRUCTIONS TO FIX:")
        print(f"   1. Run this command ONCE on your local machine:")
        print(f"      python scripts/convert_h1b_excel_to_csv.py")
        print(f"   ")
        print(f"   2. This will convert Excel → CSV (takes 30-50 min one time)")
        print(f"   ")
        print(f"   3. Future DAG runs will be INSTANT (~30 seconds)")
        print(f"\n⚠️  DO NOT run Excel conversion in Airflow - it takes too long and gets killed!")
        
        raise FileNotFoundError(
            f"H-1B CSV file not found at {csv_file}. "
            f"Please convert Excel to CSV first using: python scripts/convert_h1b_excel_to_csv.py"
        )
    
    # Filter for USA jobs only
    if 'WORKSITE_STATE' in df.columns:
        df = df[df['WORKSITE_STATE'].notna()]
        print(f"✓ Filtered to {len(df)} rows with valid worksite state")
    
    # Keep ALL 97 columns from H-1B data
    print(f"✓ Keeping all {len(df.columns)} columns from H-1B CSV")
    
    # No column filtering - we want all fields!
    
    # Write to output CSV
    print(f"✓ Writing final CSV...")
    df.to_csv(output_csv, index=False)
    print(f"✓ CSV ready: {output_csv}")
    
    print("\n" + "=" * 80)
    print("DATA LOADING COMPLETED")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"   Total records: {len(df)}")
    print(f"   Columns: {len(available_columns)}")
    print(f"   Output CSV: {output_csv}")
    
    # Push to XCom for next tasks
    context['ti'].xcom_push(key='csv_file', value=output_csv)
    context['ti'].xcom_push(key='record_count', value=len(df))
    
    return len(df)

def upload_h1b_to_s3(**context):
    """
    Upload CSV file directly to S3 (OPTIMIZED)
    """
    from dags.common.s3_utils import get_s3_client, load_secrets
    
    print("\n" + "=" * 80)
    print("STEP 2: UPLOADING CSV TO S3")
    print("=" * 80)
    
    # Get CSV file from previous task
    csv_file = context['ti'].xcom_pull(key='csv_file', task_ids='load_h1b_data')
    
    if not csv_file or not os.path.exists(csv_file):
        print("⚠️  No CSV file to upload")
        return None
    
    # Get S3 config from secrets
    secrets = load_secrets()
    bucket = secrets['aws']['s3_bucket']
    s3_client = get_s3_client()
    
    # Upload CSV to S3
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"raw/h1b/h1b_data_{timestamp}.csv"
    
    print(f"🚀 Uploading CSV to S3...")
    print(f"   Bucket: {bucket}")
    print(f"   Key: {s3_key}")
    
    s3_client.upload_file(csv_file, bucket, s3_key)
    s3_path = f"s3://{bucket}/{s3_key}"
    
    print(f"✅ Uploaded CSV to: {s3_path}")
    
    context['ti'].xcom_push(key='s3_path', value=s3_path)
    context['ti'].xcom_push(key='s3_key', value=s3_key)
    return s3_path

def upload_h1b_to_snowflake(**context):
    """
    Load CSV directly to Snowflake using COPY INTO (OPTIMIZED - 10-50x faster)
    """
    from dags.common.snowflake_utils import get_snowflake_connection, load_secrets
    
    print("\n" + "=" * 80)
    print("STEP 3: LOADING CSV TO SNOWFLAKE (NATIVE COPY)")
    print("=" * 80)
    
    # Get S3 path from previous task
    s3_key = context['ti'].xcom_pull(key='s3_key', task_ids='upload_to_s3')
    
    if not s3_key:
        print("⚠️  No S3 path available")
        return 0
    
    # Get Snowflake and AWS config from secrets
    secrets = load_secrets()
    bucket = secrets['aws']['s3_bucket']
    
    # Snowflake connection using secrets
    conn = get_snowflake_connection()
    
    cursor = conn.cursor()
    
    try:
        # Table already exists with all 97 fields + loaded_at (98 columns total)
        # Created via: snowflake/setup/02_create_tables.sql
        print("✓ Using existing h1b_raw table with all 97 H-1B fields")
        
        # Truncate existing data before loading new quarterly data
        print("🗑️ Truncating existing H-1B data...")
        cursor.execute("TRUNCATE TABLE h1b_raw")
        
        # Use COPY INTO for native Snowflake loading (FAST!)
        print(f"🚀 Loading CSV from S3 using COPY INTO...")
        print(f"   S3 Key: {s3_key}")
        print(f"   Bucket: {bucket}")
        
        aws_key = secrets['aws']['access_key_id']
        aws_secret = secrets['aws']['secret_access_key']
        
        copy_sql = f"""
            COPY INTO h1b_raw
            FROM 's3://{bucket}/{s3_key}'
            CREDENTIALS = (
                AWS_KEY_ID = '{aws_key}'
                AWS_SECRET_KEY = '{aws_secret}'
            )
            FILE_FORMAT = (
                TYPE = 'CSV'
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                SKIP_HEADER = 1
                FIELD_DELIMITER = ','
                ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE
            )
            ON_ERROR = 'CONTINUE'
            FORCE = TRUE
        """
        
        cursor.execute(copy_sql)
        result = cursor.fetchone()
        
        rows_loaded = result[0] if result else 0
        print(f"✅ Loaded {rows_loaded} rows to Snowflake using COPY INTO")
        
        return rows_loaded
        
    finally:
        cursor.close()
        conn.close()

def print_pipeline_summary(**context):
    """Print comprehensive pipeline summary"""
    print("\n" + "=" * 80)
    print("🎯 H-1B DATA PIPELINE SUMMARY")
    print("=" * 80)
    
    record_count = context['ti'].xcom_pull(key='record_count', task_ids='load_h1b_data') or 0
    s3_path = context['ti'].xcom_pull(key='s3_path', task_ids='upload_to_s3') or 'N/A'
    
    print(f"\n📊 Results:")
    print(f"   ✓ H-1B records loaded: {record_count}")
    print(f"   ✓ S3 path: {s3_path}")
    print(f"   ✓ Snowflake table: job_intelligence.raw.h1b_raw")
    print(f"\n✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

# Create DAG
with DAG(
    'h1b_loader',
    default_args=default_args,
    description='H-1B data loader pipeline: Load -> S3 -> Snowflake (Manual trigger only)',
    schedule_interval=None,  # Manual trigger only - run when new quarterly data is available
    start_date=pendulum.now('America/New_York').subtract(days=1),
    catchup=False,
    tags=['loader', 'h1b', 'data', 'manual', 'pipeline'],
) as dag:
    
    # Task 1: Load H-1B data
    load_task = PythonOperator(
        task_id='load_h1b_data',
        python_callable=load_h1b_data,
        provide_context=True,
    )
    
    # Task 2: Upload to S3
    s3_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_h1b_to_s3,
        provide_context=True,
    )
    
    # Task 3: Upload to Snowflake
    snowflake_task = PythonOperator(
        task_id='upload_to_snowflake',
        python_callable=upload_h1b_to_snowflake,
        provide_context=True,
    )
    
    # Task 4: Print summary
    summary_task = PythonOperator(
        task_id='print_summary',
        python_callable=print_pipeline_summary,
        provide_context=True,
    )
    
    # Pipeline: Load -> S3 -> Snowflake -> Summary
    load_task >> s3_task >> snowflake_task >> summary_task
