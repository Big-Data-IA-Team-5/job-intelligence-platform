"""
Airflow DAG for Internship Airtable Scraper
Scrapes all internship categories from intern-list.com Airtable bases
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scrapers.Internship_Airtable_scraper import InternshipAirtableScraper

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

def run_internship_scraper(**context):
    """
    Run the comprehensive internship Airtable scraper
    Scrapes all 20 internship categories from intern-list.com
    """
    print("=" * 80)
    print("STARTING INTERNSHIP AIRTABLE SCRAPER")
    print("=" * 80)
    
    # Configuration
    hours_lookback = 720  # 30 days
    num_workers = 5       # 5 parallel workers
    
    print(f"\n⚙️  Configuration:")
    print(f"   Time window: Last {hours_lookback} hours ({hours_lookback/24:.1f} days)")
    print(f"   Workers: {num_workers}")
    print(f"   Output: airflow/scraped_jobs/")
    
    # Initialize scraper
    scraper = InternshipAirtableScraper(
        hours_lookback=hours_lookback,
        num_workers=num_workers,
        max_retries=3
    )
    
    # Run scraper
    print(f"\n🚀 Starting internship scraper...")
    results = scraper.scrape_all_categories()
    
    # Summary
    total_jobs = sum(r.get('job_count', 0) for r in results.values())
    successful = sum(1 for r in results.values() if r.get('status') == 'success')
    failed = sum(1 for r in results.values() if r.get('status') == 'failed')
    
    print("\n" + "=" * 80)
    print("INTERNSHIP SCRAPING COMPLETED")
    print("=" * 80)
    print(f"\n📊 Results:")
    print(f"   Total internships: {total_jobs}")
    print(f"   Successful categories: {successful}/{len(results)}")
    print(f"   Failed categories: {failed}/{len(results)}")
    print(f"   Time window: Last {hours_lookback} hours")
    
    # Push metrics to XCom
    context['ti'].xcom_push(key='total_internships', value=total_jobs)
    context['ti'].xcom_push(key='successful_categories', value=successful)
    context['ti'].xcom_push(key='failed_categories', value=failed)
    context['ti'].xcom_push(key='hours_lookback', value=hours_lookback)
    
    # Return summary
    return {
        'total_internships': total_jobs,
        'successful_categories': successful,
        'failed_categories': failed,
        'time_window_hours': hours_lookback
    }

# Create DAG
with DAG(
    'internship_scraper',
    default_args=default_args,
    description='Internship Airtable scraper - scrapes all 20 internship categories from intern-list.com',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['scraper', 'airtable', 'internships', 'intern-list'],
) as dag:
    
    # Task: Run internship Airtable scraper
    scrape_internships = PythonOperator(
        task_id='scrape_internship_jobs',
        python_callable=run_internship_scraper,
        provide_context=True,
        execution_timeout=timedelta(hours=2),  # Max 2 hours
        doc_md="""
        ## Internship Airtable Scraper
        
        This task runs the comprehensive internship scraper that:
        - Scrapes **20 internship categories** from intern-list.com
        - Uses **Selenium** with deep scrolling (up to 100 scrolls per category)
        - Runs **5 parallel workers** for efficiency
        - Collects internships from the **last 30 days**
        - Saves output to `airflow/scraped_jobs/` as JSON, CSV, and Markdown
        
        ### Categories Scraped:
        - Software Engineering
        - Data Analysis
        - Machine Learning & AI
        - Product Management
        - Accounting & Finance
        - Engineering & Development
        - Business Analyst
        - Marketing
        - Cybersecurity
        - Consulting
        - Creatives & Design
        - Management & Executive
        - Public Sector & Government
        - Legal & Compliance
        - Human Resources
        - Arts & Entertainment
        - Sales
        - Customer Service & Support
        - Education & Training
        - Healthcare
        
        ### Output Files:
        - `internships_all_720h_[timestamp].json`
        - `internships_all_720h_[timestamp].csv`
        - `internships_all_720h_[timestamp].md`
        
        ### Estimated Runtime:
        - ~15-20 minutes total
        - Each category takes ~2-3 minutes
        - 5 categories run in parallel
        
        ### Source:
        All data scraped from intern-list.com Airtable bases
        """,
    )

    scrape_internships
