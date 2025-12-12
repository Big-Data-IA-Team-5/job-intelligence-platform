"""
Airflow DAG for Internship Airtable Scraper
Scrapes all internship categories from intern-list.com Airtable bases
Pipeline: Scrape -> S3 Upload -> Snowflake Upload
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pendulum
import sys
import os
import json

# Add dags folder to path for module imports
sys.path.insert(0, os.path.join(os.environ.get('AIRFLOW_HOME', '/home/airflow'), 'gcs/dags'))

# Load code dependencies from GCS (Composer-compatible)
from gcs_loader import setup_code_dependencies, get_composer_bucket

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2, minutes=45),  # 2h 45min to stay under Celery 3hr timeout
}

def scrape_internship_jobs(**context):
    """
    Scrape all internship categories from Airtable with full error handling
    """
    import signal
    import sys
    import traceback
    
    def timeout_handler(signum, frame):
        print("\n⏱️  TIMEOUT: Scraper exceeded 2h 45m limit")
        raise TimeoutError("Scraper timeout - Celery worker limit reached")
    
    try:
        # Timeout managed by Airflow's execution_timeout parameter (2h 45m)
        # No need for signal.alarm() which can interfere with proper error logging
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(9900)  # 2h 45m in seconds (slightly under Celery 3hr limit)
        
        # Load code from GCS
        print("\n" + "="*80)
        print("LOADING GCS DEPENDENCIES")
        print("="*80)
        sys.stdout.flush()
        
        bucket = get_composer_bucket()
        print(f"✅ Using bucket: {bucket}")
        sys.stdout.flush()
        
        paths = setup_code_dependencies(bucket)
        print(f"✅ Paths loaded: {paths}")
        sys.stdout.flush()
        
        from scrapers.Internship_Airtable_scraper import InternshipAirtableScraper
        from common.s3_utils import cleanup_old_s3_files
        
        print("=" * 80)
        print("STEP 1: SCRAPING INTERNSHIPS FROM AIRTABLE")
        print("=" * 80)
        sys.stdout.flush()
        
        print("\nCleaning up old S3 files...")
        sys.stdout.flush()
        cleanup_old_s3_files(prefix='raw/airtable/internships/', days_to_keep=30)
        
        # Configuration - PRODUCTION OPTIMIZED (Celery timeout = 3 hours)
        hours_lookback = 168  # 7 days (reduced from 15 to fit Celery 3hr timeout)
        num_workers = 3  # 3 workers for fast parallel scraping (16GB RAM per worker)
        
        print(f"\n⚙️  Configuration:")
        print(f"   Time window: Last {hours_lookback} hours ({hours_lookback/24:.0f} days)")
        print(f"   Workers: {num_workers}")
        print(f"   Celery timeout: 3 hours (Composer default)")
        sys.stdout.flush()
        
        # Initialize scraper
        print("\n🔧 Initializing scraper...")
        sys.stdout.flush()
        scraper = InternshipAirtableScraper(
            hours_lookback=hours_lookback,
            num_workers=num_workers,
            max_retries=2
        )
        print("✅ Scraper initialized")
        sys.stdout.flush()
        
        # Run scraper
        print(f"\n🚀 Starting internship scraper...")
        sys.stdout.flush()
        results = scraper.scrape_all_categories()
        
        # Collect all jobs
        print(f"\n📦 Collecting results...")
        sys.stdout.flush()
        all_jobs = scraper.all_jobs
        
        # Summary
        total_jobs = len(all_jobs)
        successful = sum(1 for r in results.values() if r.get('status') == 'success')
        failed = sum(1 for r in results.values() if r.get('status') == 'failed')
        
        print("\n" + "=" * 80)
        print("SCRAPING COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\n📊 Results:")
        print(f"   Total internships: {total_jobs}")
        print(f"   Successful categories: {successful}/{len(results)}")
        print(f"   Failed categories: {failed}/{len(results)}")
        sys.stdout.flush()
        
        # Cancel timeout
        signal.alarm(0)
        
        # Push to XCom for next tasks
        context['ti'].xcom_push(key='internship_jobs', value=all_jobs)
        context['ti'].xcom_push(key='job_count', value=total_jobs)
        
        return total_jobs
    
    except TimeoutError as e:
        print(f"\n⏱️  TIMEOUT ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise
    except Exception as e:
        print(f"\n❌ ERROR in scrape_internship_jobs: {str(e)}")
        import traceback
        print(traceback.format_exc())
        
        print("\n" + "=" * 80)
        print("FULL ERROR DETAILS:")
        print("=" * 80)
        import sys as sys_module
        exc_type, exc_value, exc_traceback = sys_module.exc_info()
        print(f"Type: {exc_type}")
        print(f"Value: {exc_value}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.stdout.flush()
        raise

def upload_internship_jobs_to_s3(**context):
    """
    Upload scraped internship jobs to S3
    """
    from common.s3_utils import upload_to_s3
    
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
    from common.snowflake_utils import upload_to_snowflake
    
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
    schedule_interval='0 13,19,1 * * *',  # Run 3x daily: 8 AM, 2 PM, 8 PM EST (takes ~1 hour)
    start_date=pendulum.datetime(2025, 12, 5, 8, 0, tz="America/New_York"),  # Start at 8 AM EST
    catchup=False,
    tags=['scraper', 'airtable', 'internships', 'intern-list', 'pipeline'],
) as dag:
    
    # Task 1: Scrape internship jobs
    scrape_task = PythonOperator(
        task_id='scrape_internship_jobs',
        python_callable=scrape_internship_jobs,
        provide_context=True,
        execution_timeout=timedelta(minutes=20),  # Explicit timeout for slow page loads
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
    
    # Task 4: Print summary
    # Note: DBT transformations now run independently in dag_dbt_transformations
    summary_task = PythonOperator(
        task_id='print_summary',
        python_callable=print_pipeline_summary,
        provide_context=True,
    )
    
    # Pipeline: Scrape -> S3 -> Snowflake -> Summary
    # DBT transformations run independently every 6 hours in dag_dbt_transformations
    scrape_task >> s3_task >> snowflake_task >> summary_task
