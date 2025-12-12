"""
DAG: Fortune 500 Company Scraper
Scrapes jobs from Fortune 500 company career pages using hybrid approach
Pipeline: Scrape -> S3 Upload -> Snowflake Upload
Schedule: Weekly on Mondays at 1 AM UTC
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
    """Scrape jobs from Fortune 500 companies with full error handling and real-time output"""
    import signal
    import sys
    import traceback
    
    def timeout_handler(signum, frame):
        print("\n⏱️  TIMEOUT: Scraper exceeded 8-hour limit")
        raise TimeoutError("Scraper timeout after 8 hours")
    
    try:
        # Set timeout to 8 hours (Fortune 500 needs more time, 8 workers)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(28800)  # 8 hours for 8-worker Fortune 500 scrape
        
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
        
        from scrapers.Fortune_500 import UltraSmartScraper, scrape_single_company, ProgressManager
        from common.snowflake_utils import load_secrets
        from common.s3_utils import cleanup_old_s3_files
        import pandas as pd
        from concurrent.futures import ThreadPoolExecutor
        
        print("=" * 80)
        print("STEP 1: SCRAPING FORTUNE 500 COMPANIES")
        print("=" * 80)
        sys.stdout.flush()
        
        print("\nCleaning up old S3 files...")
        sys.stdout.flush()
        cleanup_old_s3_files(prefix='raw/fortune500/', days_to_keep=30)
        
        print("\n🔐 Loading secrets...")
        sys.stdout.flush()
        secrets = load_secrets()
        openai_key = secrets['api']['openai_api_key']
        if not openai_key:
            raise ValueError("OpenAI API key not found in secrets.json")
        print("✅ Secrets loaded")
        sys.stdout.flush()
        
        # Initialize scraper - DISABLE SELENIUM for parallel processing
        # Selenium is NOT thread-safe and causes massive slowdowns with ThreadPoolExecutor
        print("\n🔧 Initializing scraper...")
        sys.stdout.flush()
        scraper = UltraSmartScraper(
            openai_key=openai_key,
            use_selenium=False  # HTTP-only mode for 10x faster parallel scraping
        )
        print("✅ Scraper initialized (HTTP-only mode for 8-worker parallel)")
        sys.stdout.flush()
        
        # Initialize progress manager
        progress = ProgressManager()
        
        # Download CSV from GCS if not exists locally
        csv_path = '/tmp/airflow_code/fortune500_career_pages_validated.csv'
        if not os.path.exists(csv_path):
            print("\n📥 Downloading Fortune 500 CSV from GCS...")
            sys.stdout.flush()
            from google.cloud import storage
            client = storage.Client()
            bucket_obj = client.bucket(bucket.replace('gs://', ''))
            blob = bucket_obj.blob('data/fortune500_career_pages_validated.csv')
            blob.download_to_filename(csv_path)
            print(f"✅ Downloaded Fortune 500 CSV from GCS")
            sys.stdout.flush()
        
        print("\n📖 Reading company list...")
        sys.stdout.flush()
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
        print(f"   Max workers: 8 (optimized for Fortune 500 HTTP-only)")
        print(f"   Time window: Last 15 days")
        print(f"   Timeout: 8 hours")
        sys.stdout.flush()
        
        all_jobs = []
        successful_companies = 0
        failed_companies = 0
        
        # Scrape companies in parallel - PRODUCTION OPTIMIZED
        print("\n🚀 Starting scraper with 8 workers...")
        sys.stdout.flush()
        try:
            with ThreadPoolExecutor(max_workers=8) as executor:  # 8 workers for Fortune 500
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
                for idx, future in enumerate(futures):
                    try:
                        result = future.result(timeout=300)  # 5 min timeout per company (HTTP-only is fast)
                        if result['success'] and result['jobs']:
                            all_jobs.extend(result['jobs'])
                            progress.save_progress(result['company'])
                            successful_companies += 1
                            if (idx + 1) % 10 == 0:
                                print(f"✅ Progress: {idx + 1}/{len(futures)} companies")
                                sys.stdout.flush()
                        else:
                            failed_companies += 1
                    except Exception as e:
                        failed_companies += 1
                        print(f"⚠️  Company {idx + 1} failed: {str(e)[:100]}")
                        sys.stdout.flush()
        
        finally:
            # Cleanup Selenium drivers
            print("\n🧹 Cleaning up resources...")
            sys.stdout.flush()
            if hasattr(scraper, 'http') and hasattr(scraper.http, 'cleanup_driver'):
                scraper.http.cleanup_driver()
        
        # Cancel timeout
        signal.alarm(0)
        
        print("\n" + "=" * 80)
        print("SCRAPING COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print(f"\n📊 Results:")
        print(f"   Total jobs scraped: {len(all_jobs)}")
        print(f"   Successful companies: {successful_companies}")
        print(f"   Failed companies: {failed_companies}")
        sys.stdout.flush()
        
        # Push to XCom for next tasks
        context['ti'].xcom_push(key='fortune500_jobs', value=all_jobs)
        context['ti'].xcom_push(key='job_count', value=len(all_jobs))
        
        return len(all_jobs)
    
    except TimeoutError as e:
        print(f"\n⏱️  TIMEOUT ERROR after 8 hours: {str(e)}")
        print(traceback.format_exc())
        sys.stdout.flush()
        raise
    except Exception as e:
        print(f"\n❌ ERROR in scrape_fortune500_jobs: {str(e)}")
        print(traceback.format_exc())
        
        print("\n" + "=" * 80)
        print("FULL ERROR DETAILS:")
        print("=" * 80)
        import sys as sys_module
        exc_type, exc_value, exc_traceback = sys_module.exc_info()
        print(f"Type: {exc_type}")
        print(f"Value: {exc_value}")
        print(f"Traceback:")
        print(traceback.format_exc())
        sys.stdout.flush()
        raise

def upload_fortune500_jobs_to_s3(**context):
    """
    Upload scraped Fortune 500 jobs to S3
    """
    from common.s3_utils import upload_to_s3
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
    from common.snowflake_utils import upload_to_snowflake
    
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
        execution_timeout=timedelta(minutes=30),  # Explicit timeout for Fortune 500 (longer due to multiple sites)
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
