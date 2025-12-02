"""
DAG 5: Fortune 500 Company Scraper
Scrapes jobs from Fortune 500 company career pages using hybrid approach
Schedule: Weekly on Mondays at 1 AM UTC
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add scrapers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scrapers'))

from Fortune_500 import UltraSmartScraper, scrape_single_company, ProgressManager
from common.snowflake_utils import upload_to_snowflake, load_secrets
from common.s3_utils import upload_to_s3
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import json

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=15),
    'execution_timeout': timedelta(hours=6),  # Prevent zombie processes
}

def scrape_fortune500_jobs(**context):
    """Scrape jobs from Fortune 500 companies"""
    from common.s3_utils import cleanup_old_s3_files
    
    # Clean up old files first (files older than 30 days)
    print("Cleaning up old S3 files...")
    cleanup_old_s3_files(prefix='raw/fortune500/', days_to_keep=30)
    
    # Get OpenAI API key from secrets
    secrets = load_secrets()
    openai_key = secrets['api']['openai_api_key']
    if not openai_key:
        raise ValueError("OpenAI API key not found in secrets.json")
    
    # Initialize scraper
    scraper = UltraSmartScraper(
        openai_key=openai_key,
        use_selenium=True
    )
    
    # Initialize progress manager
    progress = ProgressManager()
    
    # Load companies from CSV
    csv_path = os.path.join(
        os.path.dirname(__file__),
        '../../data/fortune500_career_pages_validated.csv'
    )
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Fortune 500 CSV not found: {csv_path}")
    
    companies = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = pd.read_csv(f)
        for _, row in reader.iterrows():
            companies.append({
                'name': row['company_name'],
                'url': row['final_career_url']
            })
    
    # Filter out completed companies
    companies_to_scrape = [
        c for c in companies 
        if not progress.is_completed(c['name'])
    ][:25]  # Limit to 25 companies per daily run (balance between coverage and runtime)
    
    print(f"Scraping {len(companies_to_scrape)} Fortune 500 companies")
    
    all_jobs = []
    
    # Scrape companies in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
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
            result = future.result()
            if result['success'] and result['jobs']:
                all_jobs.extend(result['jobs'])
                progress.save_progress(result['company'])
    
    print(f"Total jobs scraped from Fortune 500: {len(all_jobs)}")
    
    # Push to XCom
    context['task_instance'].xcom_push(key='jobs_data', value=all_jobs)
    context['task_instance'].xcom_push(key='job_count', value=len(all_jobs))
    
    return len(all_jobs)

def upload_jobs_to_s3(**context):
    """Upload scraped jobs to S3 as timestamped file (appends, not replaces)"""
    jobs = context['task_instance'].xcom_pull(key='jobs_data', task_ids='scrape_fortune500')
    
    if not jobs:
        print("No jobs to upload")
        return
    
    # Use timestamp in filename to append, not replace
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"raw/fortune500/jobs_{timestamp}.json"
    
    s3_path = upload_to_s3(jobs, s3_key)
    print(f"Uploaded to S3: {s3_path}")
    
    context['task_instance'].xcom_push(key='s3_path', value=s3_path)
    return s3_path

with DAG(
    'fortune500_scraper_dag',
    default_args=default_args,
    description='Scrape jobs from Fortune 500 company career pages weekly (7-8 hour runtime)',
    schedule_interval='0 18 * * 6',  # Weekly on Saturday at 6 PM UTC (runs overnight, finishes Sunday)
    start_date=days_ago(1),
    catchup=False,
    tags=['scraping', 'fortune500', 'companies', 'weekly'],
) as dag:
    
    scrape_task = PythonOperator(
        task_id='scrape_fortune500',
        python_callable=scrape_fortune500_jobs,
        provide_context=True,
        execution_timeout=timedelta(hours=4),  # Fortune 500 scraping takes longer
    )
    
    upload_s3_task = PythonOperator(
        task_id='upload_to_s3',
        python_callable=upload_jobs_to_s3,
        provide_context=True,
    )
    
    # Pipeline ends at S3 - Snowflake loading will be added later
    scrape_task >> upload_s3_task
