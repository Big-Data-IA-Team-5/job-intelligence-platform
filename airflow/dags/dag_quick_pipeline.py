"""
DAG: Test Pipeline (Quick End-to-End Test)
Tests the entire pipeline with minimal data for fast validation
Pipeline: Scrape 2 categories -> Upload to Snowflake -> DBT -> Summary
Schedule: Manual trigger only
Duration: ~5-10 minutes
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pendulum
import sys
import os

# Add dags folder to path for module imports
sys.path.insert(0, os.path.join(os.environ.get('AIRFLOW_HOME', '/home/airflow'), 'gcs/dags'))

# Load code dependencies from GCS (Composer-compatible)
from gcs_loader import setup_code_dependencies, get_composer_bucket

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'execution_timeout': timedelta(minutes=45),  # Increased for DBT h1b_matched_jobs
}

def test_scrape_jobs(**context):
    """Quick test scrape - only 2 categories with 1 worker"""
    # Load code from GCS
    bucket = get_composer_bucket()
    paths = setup_code_dependencies(bucket)
    
    from scrapers.Airtable_Comprehensive_scraper import ComprehensiveAirtableScraper
    import json
    
    print("=" * 80)
    print("🧪 TEST SCRAPE - 2 CATEGORIES ONLY")
    print("=" * 80)
    
    # Configuration for FAST testing
    hours_lookback = 96       # Last 4 days to ensure we get some jobs
    num_workers = 1           # Single worker for predictable testing
    test_categories = [
        'Data_Engineer'
    ]  # Only 1 category for fastest testing
    
    print(f"\n⚙️  Test Configuration:")
    print(f"   Time window: Last {hours_lookback} hours")
    print(f"   Categories: {len(test_categories)} (fastest test)")
    print(f"   Workers: {num_workers}")
    
    # Initialize scraper
    scraper = ComprehensiveAirtableScraper(
        hours_lookback=hours_lookback,
        num_workers=num_workers,
        max_retries=2  # Fewer retries for faster testing
    )
    
    # Scrape only test categories
    results = scraper.scrape_all_categories(specific_categories=test_categories)
    
    # Get flat list of all jobs from scraper
    all_jobs = scraper.all_jobs
    
    print("\n" + "=" * 80)
    print("TEST SCRAPING COMPLETED")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"   Total jobs scraped: {len(all_jobs)}")
    print(f"   Categories processed: {len(test_categories)}")
    print(f"   Successful: {sum(1 for r in results.values() if r.get('status') == 'success')}/{len(results)}")
    
    # Save to test file (create directory if needed)
    output_dir = '/tmp/scraped_jobs'
    os.makedirs(output_dir, exist_ok=True)
    output_file = f'{output_dir}/test_pipeline_jobs.json'
    with open(output_file, 'w') as f:
        json.dump(all_jobs, f, indent=2)
    
    print(f"\n✅ Saved to: {output_file}")
    
    # Push to XCom for next task
    context['task_instance'].xcom_push(key='jobs_file', value=output_file)
    context['task_instance'].xcom_push(key='jobs_count', value=len(all_jobs))
    
    return len(all_jobs)


def test_upload_to_snowflake(**context):
    """Upload test data to Snowflake"""
    # Load code from GCS
    bucket = get_composer_bucket()
    paths = setup_code_dependencies(bucket)
    
    import json
    import snowflake.connector
    from common.snowflake_utils import upload_to_snowflake
    
    print("=" * 80)
    print("🧪 TEST UPLOAD TO SNOWFLAKE")
    print("=" * 80)
    
    # Get scraped jobs from previous task
    jobs_file = context['task_instance'].xcom_pull(
        task_ids='test_scrape_jobs',
        key='jobs_file'
    )
    
    # Load jobs
    with open(jobs_file, 'r') as f:
        jobs = json.load(f)
    
    print(f"\n📊 Uploading {len(jobs)} test jobs to Snowflake...")
    
    # Upload to Snowflake (credentials loaded automatically from secrets)
    rows = upload_to_snowflake(
        data=jobs,
        table='jobs_raw'
        # database and schema will be loaded from secrets.json automatically
    )
    
    print("\n" + "=" * 80)
    print("TEST UPLOAD COMPLETED")
    print("=" * 80)
    print(f"\n✅ Uploaded {rows} rows to Snowflake")
    
    return rows


def test_print_summary(**context):
    """Print test pipeline summary"""
    from common.snowflake_utils import load_secrets
    import snowflake.connector
    
    print("=" * 80)
    print("🧪 TEST PIPELINE SUMMARY")
    print("=" * 80)
    
    # Get counts from previous tasks
    jobs_scraped = context['task_instance'].xcom_pull(
        task_ids='test_scrape_jobs',
        key='jobs_count'
    )
    
    jobs_uploaded = context['task_instance'].xcom_pull(
        task_ids='test_upload_to_snowflake'
    )
    
    print(f"\n📊 Pipeline Results:")
    print(f"   Jobs scraped: {jobs_scraped}")
    print(f"   Jobs uploaded: {jobs_uploaded}")
    
    # Query Snowflake for actual counts
    secrets = load_secrets()
    sf_creds = secrets['snowflake']
    
    conn = snowflake.connector.connect(
        user=sf_creds['user'],
        password=sf_creds['password'],
        account=sf_creds['account'],
        warehouse=sf_creds['warehouse'],
        database=sf_creds['database'],
        schema=sf_creds['schema'],
        role=sf_creds['role']
    )
    
    cursor = conn.cursor()
    
    # Count records in each table
    tables = [
        ('raw.jobs_raw', 'Raw Jobs'),
        ('processed_staging.stg_jobs', 'Staged Jobs'),
        ('processed_staging.dedup_jobs', 'Deduplicated Jobs'),
        ('processed_processing.h1b_matched_jobs', 'H1B Matched'),
        ('processed_processing.classified_jobs', 'Classified Jobs'),
        ('processed_processing.embedded_jobs', 'Embedded Jobs'),
        ('processed_marts.job_intelligence_mart', 'Final Mart')
    ]
    
    print(f"\n📈 Snowflake Table Counts:")
    for table_path, name in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table_path}")
            count = cursor.fetchone()[0]
            print(f"   {name}: {count:,}")
        except Exception as e:
            print(f"   {name}: ⚠️  {str(e)[:50]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ TEST PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("\n💡 If all tasks passed, your full pipeline is working correctly!")


# Define the DAG
with DAG(
    'quick_pipeline_test',
    default_args=default_args,
    description='Quick end-to-end pipeline test (5-10 min)',
    schedule=None,  # Manual trigger only (Airflow 2.x)
    start_date=pendulum.today('America/New_York').add(days=-1),
    catchup=False,
    tags=['test', 'pipeline', 'quick']
) as dag:
    
    # Task 1: Test scrape (2 categories, 1 worker)
    scrape_task = PythonOperator(
        task_id='test_scrape_jobs',
        python_callable=test_scrape_jobs,
        execution_timeout=timedelta(minutes=15)  # Explicit timeout for slow page loads
    )
    
    # Task 2: Upload to Snowflake
    upload_task = PythonOperator(
        task_id='test_upload_to_snowflake',
        python_callable=test_upload_to_snowflake
    )
    
    # Task 3: Print summary (DBT runs independently in dag_dbt_transformations)
    summary_task = PythonOperator(
        task_id='test_print_summary',
        python_callable=test_print_summary
    )
    
    # Define task dependencies (DBT now runs as separate DAG)
    scrape_task >> upload_task >> summary_task
