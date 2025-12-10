"""
DAG: Fortune 500 Company Scraper
Scrapes jobs from Fortune 500 company career pages using hybrid approach
Pipeline: Scrape -> S3 Upload -> Snowflake Upload
Schedule: Weekly on Mondays at 1 AM UTC
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pendulum
import sys
import os
import json

# Add parent directories to path
sys.path.insert(0, '/opt/airflow')
sys.path.insert(0, '/opt/airflow/scrapers')

# Import only lightweight modules at top level
# Heavy imports moved inside task functions to prevent DAG import timeout

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=15),
    'execution_timeout': timedelta(hours=8),  # 8 hours for 50 companies with fallbacks
}

def scrape_fortune500_jobs(**context):
    """Scrape jobs from Fortune 500 companies"""
    # Lazy imports to prevent DAG import timeout
    from scrapers.Fortune_500 import UltraSmartScraper, scrape_single_company, ProgressManager
    from dags.common.snowflake_utils import load_secrets
    from dags.common.s3_utils import cleanup_old_s3_files
    import pandas as pd
    from concurrent.futures import ThreadPoolExecutor
    
    print("=" * 80)
    print("STEP 1: SCRAPING FORTUNE 500 COMPANIES")
    print("=" * 80)
    
    # Clean up old files first (files older than 30 days)
    print("\nCleaning up old S3 files...")
    cleanup_old_s3_files(prefix='raw/fortune500/', days_to_keep=30)
    
    # Get OpenAI API key from secrets
    secrets = load_secrets()
    openai_key = secrets['api']['openai_api_key']
    if not openai_key:
        raise ValueError("OpenAI API key not found in secrets.json")
    
    # Initialize scraper - DISABLE SELENIUM for parallel processing
    # Selenium is NOT thread-safe and causes massive slowdowns with ThreadPoolExecutor
    scraper = UltraSmartScraper(
        openai_key=openai_key,
        use_selenium=False  # HTTP-only mode for 10x faster parallel scraping
    )
    
    # Initialize progress manager
    progress = ProgressManager()
    
    # Load companies from CSV
    # Check Docker mount first, then local path
    csv_path = '/opt/airflow/data/fortune500_career_pages_validated.csv'
    if not os.path.exists(csv_path):
        csv_path = os.path.join(
            os.path.dirname(__file__),
            '../../data/fortune500_career_pages_validated.csv'
        )
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fortune 500 CSV not found at: {csv_path}")
    
    companies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = pd.read_csv(f)
        for _, row in reader.iterrows():
            companies.append({
                'name': row['company_name'],
                'url': row['final_career_url']
            })
    
    # Filter out completed companies - PRODUCTION OPTIMIZED
    companies_to_scrape = [
        c for c in companies 
        if not progress.is_completed(c['name'])
    ][:200]  # Scrape 200 companies per run (increased from 50)
    
    print(f"\n⚙️  Configuration:")
    print(f"   Total companies in CSV: {len(companies)}")
    print(f"   Companies to scrape: {len(companies_to_scrape)}")
    print(f"   Max workers: 16")  # 16 workers for FAST scraping of 500 companies!
    print(f"   Time window: Last 15 days")
    
    all_jobs = []
    
    # Scrape companies in parallel - PRODUCTION OPTIMIZED
    try:
        with ThreadPoolExecutor(max_workers=8) as executor:  # Using 8 workers for optimal performance
            futures = []
            for idx, company_info in enumerate(companies_to_scrape):
                future = executor.submit(
                    scrape_single_company,
                    company_info,
                    scraper,
                    progress,
                    idx
                )
                futures.append(future)
            
            # Collect results
            for future in futures:
                try:
                    result = future.result(timeout=300)  # 5 min timeout per company (HTTP-only is fast)
                    if result['success'] and result['jobs']:
                        all_jobs.extend(result['jobs'])
                        progress.save_progress(result['company'])
                except Exception as e:
                    print(f"⚠️  Company failed: {str(e)[:100]}")
    
    finally:
        # Cleanup Selenium drivers
        print("\n🧹 Cleaning up Selenium drivers...")
        if hasattr(scraper, 'http') and hasattr(scraper.http, 'cleanup_driver'):
            scraper.http.cleanup_driver()
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETED")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"   Total jobs scraped: {len(all_jobs)}")
    print(f"   Companies processed: {len(companies_to_scrape)}")
    
    # Push to XCom for next tasks
    context['ti'].xcom_push(key='fortune500_jobs', value=all_jobs)
    context['ti'].xcom_push(key='job_count', value=len(all_jobs))
    
    return len(all_jobs)

def upload_fortune500_jobs_to_s3(**context):
    """
    Upload scraped Fortune 500 jobs to S3
    """
    from dags.common.s3_utils import upload_to_s3
    import pandas as pd
    
    print("\n" + "=" * 80)
    print("STEP 2: UPLOADING TO S3")
    print("=" * 80)
    
    # Get jobs from previous task
    fortune500_jobs = context['ti'].xcom_pull(key='fortune500_jobs', task_ids='scrape_fortune500_jobs')
    
    if not fortune500_jobs:
        print("⚠️  No jobs to upload")
        return None
    
    # Upload to S3
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"raw/fortune500/fortune500_jobs_{timestamp}.json"
    s3_path = upload_to_s3(fortune500_jobs, s3_key)
    
    print(f"✅ Uploaded {len(fortune500_jobs)} jobs to: {s3_path}")
    
    context['ti'].xcom_push(key='s3_path', value=s3_path)
    return s3_path

def upload_fortune500_jobs_to_snowflake(**context):
    """
    Upload scraped Fortune 500 jobs to Snowflake
    """
    from dags.common.snowflake_utils import upload_to_snowflake
    
    print("\n" + "=" * 80)
    print("STEP 3: UPLOADING TO SNOWFLAKE")
    print("=" * 80)
    
    # Get jobs from scraping task
    fortune500_jobs = context['ti'].xcom_pull(key='fortune500_jobs', task_ids='scrape_fortune500_jobs')
    
    if not fortune500_jobs:
        print("⚠️  No jobs to upload")
        return 0
    
    # Upload to Snowflake
    rows = upload_to_snowflake(
        data=fortune500_jobs,
        table='jobs_raw',
        database='job_intelligence',
        schema='raw'
    )
    
    print(f"✅ Inserted {rows} rows to Snowflake")
    return rows

def print_pipeline_summary(**context):
    """Print comprehensive pipeline summary"""
    print("\n" + "=" * 80)
    print("🎯 FORTUNE 500 PIPELINE SUMMARY")
    print("=" * 80)
    
    job_count = context['ti'].xcom_pull(key='job_count', task_ids='scrape_fortune500_jobs') or 0
    s3_path = context['ti'].xcom_pull(key='s3_path', task_ids='upload_to_s3') or 'N/A'
    
    print(f"\n📊 Results:")
    print(f"   ✓ Jobs scraped: {job_count}")
    print(f"   ✓ S3 path: {s3_path}")
    print(f"   ✓ Snowflake table: job_intelligence.raw.jobs_raw")
    print(f"\n✅ PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

# Create DAG
with DAG(
    'fortune500_scraper',
    default_args=default_args,
    description='Fortune 500 scraper pipeline: Scrape -> S3 -> Snowflake',
    schedule_interval='0 5 * * *',  # Run once daily at 12:00 AM EST (takes ~2 hours)
    start_date=pendulum.datetime(2025, 12, 5, 0, 0, tz="America/New_York"),  # Start at 12 AM EST
    catchup=False,
    tags=['scraper', 'fortune500', 'companies', 'weekly', 'pipeline'],
) as dag:
    
    # Task 1: Scrape Fortune 500 jobs
    scrape_task = PythonOperator(
        task_id='scrape_fortune500_jobs',
        python_callable=scrape_fortune500_jobs,
        provide_context=True,
    )
    
    # Task 2: Upload to S3
    s3_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_fortune500_jobs_to_s3,
        provide_context=True,
    )
    
    # Task 3: Upload to Snowflake
    snowflake_task = PythonOperator(
        task_id='upload_to_snowflake',
        python_callable=upload_fortune500_jobs_to_snowflake,
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
