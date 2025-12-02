"""
DAG 3: H-1B Data Loader
Loads H-1B disclosure data into Snowflake from Excel file
Schedule: Weekly on Sundays at 3 AM UTC
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from common.snowflake_utils import upload_to_snowflake

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def load_h1b_data(**context):
    """Load H-1B data from Excel file"""
    from common.s3_utils import cleanup_old_s3_files
    
    # Clean up old H1B files in S3 (if any)
    print("Cleaning up old S3 files...")
    cleanup_old_s3_files(prefix='raw/h1b/', days_to_keep=30)
    
    # Path to H-1B data file
    data_file = os.path.join(
        os.path.dirname(__file__),
        '../../data/LCA_Disclosure_Data_FY2025_Q3.xlsx'
    )
    
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"H-1B data file not found: {data_file}")
    
    print(f"Loading H-1B data from: {data_file}")
    
    # Read Excel file
    df = pd.read_excel(data_file)
    
    # Filter for USA jobs only
    if 'WORKSITE_STATE' in df.columns:
        df = df[df['WORKSITE_STATE'].notna()]
    
    # Select relevant columns
    columns_to_keep = [
        'CASE_NUMBER',
        'EMPLOYER_NAME',
        'JOB_TITLE',
        'SOC_TITLE',
        'WORKSITE_CITY',
        'WORKSITE_STATE',
        'WAGE_RATE_OF_PAY_FROM',
        'WAGE_RATE_OF_PAY_TO',
        'WAGE_UNIT_OF_PAY',
        'H1B_DEPENDENT',
        'WILLFUL_VIOLATOR'
    ]
    
    available_columns = [col for col in columns_to_keep if col in df.columns]
    df = df[available_columns]
    
    # Convert to dict for upload
    h1b_data = df.to_dict('records')
    
    print(f"Loaded {len(h1b_data)} H-1B records")
    
    context['task_instance'].xcom_push(key='h1b_data', value=h1b_data)
    context['task_instance'].xcom_push(key='record_count', value=len(h1b_data))
    
    return len(h1b_data)

def upload_h1b_to_s3(**context):
    """Upload H1B data to S3 as timestamped JSON file"""
    from common.s3_utils import upload_to_s3
    
    h1b_data = context['task_instance'].xcom_pull(key='h1b_data', task_ids='load_h1b')
    
    if not h1b_data:
        print("No H1B data to upload")
        return
    
    # Use timestamp in filename to append, not replace
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"raw/h1b/h1b_data_{timestamp}.json"
    
    s3_path = upload_to_s3(h1b_data, s3_key)
    print(f"Uploaded to S3: {s3_path}")
    
    context['task_instance'].xcom_push(key='s3_path', value=s3_path)
    return s3_path

with DAG(
    'h1b_loader_dag',
    default_args=default_args,
    description='Load H-1B disclosure data into Snowflake (Manual trigger only - run when new data available)',
    schedule_interval=None,  # Manual trigger only - no automatic schedule
    start_date=days_ago(1),
    catchup=False,
    tags=['loading', 'h1b', 'data', 'manual'],
) as dag:
    
    load_task = PythonOperator(
        task_id='load_h1b_data',
        python_callable=load_h1b_data,
        provide_context=True,
    )
    
    upload_s3_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_h1b_to_s3,
        provide_context=True,
    )
    
    # Pipeline ends at S3 - Snowflake loading will be added later
    load_task >> upload_s3_task
