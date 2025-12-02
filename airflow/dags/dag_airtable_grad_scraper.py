"""
Airflow DAG for Airtable New Grad Job Scraper
Scrapes all new grad job categories from Airtable individually with deep scrolling
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scrapers.Airtable_Comprehensive_scraper import ComprehensiveAirtableScraper

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
    'execution_timeout': timedelta(hours=2),  # Prevent zombie processes
}

def run_comprehensive_airtable_scraper(**context):
    """
    Run the comprehensive Airtable scraper for new grad jobs
    Scrapes all categories individually with deep scrolling
    """
    print("=" * 80)
    print("STARTING AIRTABLE NEW GRAD JOB SCRAPER")
    print("=" * 80)
    
    # Configuration
    hours_lookback = 720  # 30 days
    num_workers = 5       # 5 parallel workers
    
    print(f"\n⚙️  Configuration:")
    print(f"   Time window: Last {hours_lookback} hours ({hours_lookback/24:.1f} days)")
    print(f"   Workers: {num_workers}")
    print(f"   Output: data/scraped/")
    
    # Initialize scraper
    scraper = ComprehensiveAirtableScraper(
        hours_lookback=hours_lookback,
        num_workers=num_workers,
        max_retries=3
    )
    
    # Run scraper
    print(f"\n🚀 Starting scraper...")
    results = scraper.scrape_all_categories()
    
    # Summary
    total_jobs = sum(r.get('job_count', 0) for r in results.values())
    successful = sum(1 for r in results.values() if r.get('status') == 'success')
    failed = sum(1 for r in results.values() if r.get('status') == 'failed')
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETED")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"   Total jobs: {total_jobs}")
    print(f"   Successful categories: {successful}/{len(results)}")
    print(f"   Failed categories: {failed}/{len(results)}")
    print(f"   Time window: Last {hours_lookback} hours")
    
    # Push metrics to XCom
    context['ti'].xcom_push(key='total_jobs', value=total_jobs)
    context['ti'].xcom_push(key='successful_categories', value=successful)
    context['ti'].xcom_push(key='failed_categories', value=failed)
    context['ti'].xcom_push(key='hours_lookback', value=hours_lookback)
    
    # Return summary
    return {
        'total_jobs': total_jobs,
        'successful_categories': successful,
        'failed_categories': failed,
        'time_window_hours': hours_lookback
    }

# Create DAG
with DAG(
    'airtable_grad_scraper',
    default_args=default_args,
    description='Airtable new grad job scraper - scrapes all grad job categories individually',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['scraper', 'airtable', 'new-grad', 'jobs'],
) as dag:
    
    # Task: Run comprehensive Airtable scraper
    scrape_airtable = PythonOperator(
        task_id='scrape_airtable_grad_jobs',
        python_callable=run_comprehensive_airtable_scraper,
        provide_context=True,
        execution_timeout=timedelta(hours=2),  # Max 2 hours
        doc_md="""
        ## Airtable New Grad Job Scraper
        
        This task runs the comprehensive Airtable scraper that:
        - Scrapes **21 job categories** individually
        - Uses **Selenium** with deep scrolling (up to 100 scrolls per category)
        - Runs **5 parallel workers** for efficiency
        - Collects jobs from the **last 30 days**
        - Saves output to `data/scraped/` as JSON, CSV, and Markdown
        
        ### Categories Scraped:
        - Software Engineering
        - Data Engineer
        - Machine Learning & AI
        - Cyber Security
        - Engineering & Development
        - Data Analyst
        - Business Analyst
        - Product Management
        - Project Manager
        - Marketing
        - Sales
        - Consulting
        - Management & Executive
        - Accounting & Finance
        - Human Resources
        - Customer Service & Support
        - Legal & Compliance
        - Creatives & Design
        - Arts & Entertainment
        - Education & Training
        - Health Care
        
        ### Output Files:
        - `airtable_all_720h_[timestamp].json`
        - `airtable_all_720h_[timestamp].csv`
        - `airtable_all_720h_[timestamp].md`
        
        ### Estimated Runtime:
        - ~12-15 minutes total
        - Each category takes ~2-3 minutes
        - 5 categories run in parallel
        """,
    )

    scrape_airtable
