"""
Airflow DAG for Internship Airtable Scraper
Scrapes all internship categories from intern-list.com Airtable bases
Pipeline: Scrape -> S3 Upload -> Snowflake Upload
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os
import json

# Add parent directory to path for Docker
sys.path.insert(0, '/opt/airflow')

# Import only lightweight modules at top level
# Heavy imports moved inside task functions to prevent DAG import timeout

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=8),  # 8 hours for 15 days of data scraping
}

def scrape_internship_jobs(**context):
    """
    Scrape all internship categories from Airtable
    """
    # Lazy imports to prevent DAG import timeout
    from scrapers.Internship_Airtable_scraper import InternshipAirtableScraper
    from dags.common.s3_utils import cleanup_old_s3_files
    
    print("=" * 80)
    print("STEP 1: SCRAPING INTERNSHIPS FROM AIRTABLE")
    print("=" * 80)
    
    # Clean up old S3 files first (files older than 30 days)
    print("\nCleaning up old S3 files...")
    cleanup_old_s3_files(prefix='raw/airtable/internships/', days_to_keep=30)
    
    # Configuration - PRODUCTION OPTIMIZED
    hours_lookback = 360  # 15 days (extended to get more job data)
    num_workers = 3       # 3 parallel workers (reduced to prevent Selenium Grid overload)
    
    print(f"\n⚙️  Configuration:")
    print(f"   Time window: Last {hours_lookback} hours ({hours_lookback/24:.0f} days)")
    print(f"   Workers: {num_workers}")
    
    # Initialize scraper
    scraper = InternshipAirtableScraper(
        hours_lookback=hours_lookback,
        num_workers=num_workers,
        max_retries=3
    )
    
    # Run scraper
    print(f"\n🚀 Starting internship scraper...")
    results = scraper.scrape_all_categories()
    
    # Collect all jobs
    all_jobs = scraper.all_jobs
    
    # Summary
    total_jobs = len(all_jobs)
    successful = sum(1 for r in results.values() if r.get('status') == 'success')
    failed = sum(1 for r in results.values() if r.get('status') == 'failed')
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETED")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"   Total internships: {total_jobs}")
    print(f"   Successful categories: {successful}/{len(results)}")
    print(f"   Failed categories: {failed}/{len(results)}")
    
    # Push to XCom for next tasks
    context['ti'].xcom_push(key='internship_jobs', value=all_jobs)
    context['ti'].xcom_push(key='job_count', value=total_jobs)
    
    return total_jobs

def upload_internship_jobs_to_s3(**context):
    """
    Upload scraped internship jobs to S3
    """
    from dags.common.s3_utils import upload_to_s3
    
    print("\n" + "=" * 80)
    print("STEP 2: UPLOADING TO S3")
    print("=" * 80)
    
    # Get jobs from previous task
    internship_jobs = context['ti'].xcom_pull(key='internship_jobs', task_ids='scrape_internship_jobs')
    
    if not internship_jobs:
        print("⚠️  No jobs to upload")
        return None
    
    # Upload to S3
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"raw/airtable/internships/internship_jobs_{timestamp}.json"
    s3_path = upload_to_s3(internship_jobs, s3_key)
    
    print(f"✅ Uploaded {len(internship_jobs)} jobs to: {s3_path}")
    
    context['ti'].xcom_push(key='s3_path', value=s3_path)
    return s3_path

def upload_internship_jobs_to_snowflake(**context):
    """
    Upload scraped internship jobs to Snowflake
    """
    from dags.common.snowflake_utils import upload_to_snowflake
    
    print("\n" + "=" * 80)
    print("STEP 3: UPLOADING TO SNOWFLAKE")
    print("=" * 80)
    
    # Get jobs from scraping task
    internship_jobs = context['ti'].xcom_pull(key='internship_jobs', task_ids='scrape_internship_jobs')
    
    if not internship_jobs:
        print("⚠️  No jobs to upload")
        return 0
    
    # Upload to Snowflake
    rows = upload_to_snowflake(
        data=internship_jobs,
        table='jobs_raw',
        database='job_intelligence',
        schema='raw'
    )
    
    print(f"✅ Inserted {rows} rows to Snowflake")
    return rows

def print_pipeline_summary(**context):
    """Print comprehensive pipeline summary"""
    print("\n" + "=" * 80)
    print("🎯 INTERNSHIP JOBS PIPELINE SUMMARY")
    print("=" * 80)
    
    job_count = context['ti'].xcom_pull(key='job_count', task_ids='scrape_internship_jobs') or 0
    s3_path = context['ti'].xcom_pull(key='s3_path', task_ids='upload_to_s3') or 'N/A'
    
    print(f"\n📊 Results:")
    print(f"   ✓ Internships scraped: {job_count}")
    print(f"   ✓ S3 path: {s3_path}")
    print(f"   ✓ Snowflake table: job_intelligence.raw.jobs_raw")
    print(f"\n✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

# Create DAG
with DAG(
    'internship_scraper',
    default_args=default_args,
    description='Internship scraper pipeline: Scrape -> S3 -> Snowflake',
    schedule_interval='0 4 * * *',  # Run daily at 4:00 AM UTC
    start_date=datetime(2025, 12, 5, 2, 0),  # Start today at 2 AM
    catchup=False,
    tags=['scraper', 'airtable', 'internships', 'intern-list', 'pipeline'],
) as dag:
    
    # Task 1: Scrape internship jobs
    scrape_task = PythonOperator(
        task_id='scrape_internship_jobs',
        python_callable=scrape_internship_jobs,
        provide_context=True,
    )
    
    # Task 2: Upload to S3
    s3_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_internship_jobs_to_s3,
        provide_context=True,
    )
    
    # Task 3: Upload to Snowflake
    snowflake_task = PythonOperator(
        task_id='upload_to_snowflake',
        python_callable=upload_internship_jobs_to_snowflake,
        provide_context=True,
    )
    
    # Task 4: Run dbt transformations (transforms raw -> processed)
    # Includes: classified_jobs, embedded_jobs (generates embeddings), jobs_processed
    dbt_task = BashOperator(
        task_id='run_dbt_transformations',
        bash_command='export PATH="/home/airflow/.local/bin:$PATH" && cd /opt/airflow/dbt && dbt run --profiles-dir . --target prod',
        env={
            'DBT_PROFILES_DIR': '/opt/airflow/dbt',
        },
        trigger_rule='all_done',  # Continue even if previous tasks fail
    )
    
    # Task 5: Print summary
    summary_task = PythonOperator(
        task_id='print_summary',
        python_callable=print_pipeline_summary,
        provide_context=True,
    )
    
    # Pipeline: Scrape -> S3 -> Snowflake -> dbt (includes embeddings) -> Summary
    scrape_task >> s3_task >> snowflake_task >> dbt_task >> summary_task
