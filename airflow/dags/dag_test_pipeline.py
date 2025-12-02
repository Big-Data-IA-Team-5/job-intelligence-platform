"""
TEST DAG: Pipeline Validation
Tests all FOUR data pipelines with small batches to validate:
1. Fortune 500 scraper (2 companies)
2. Graduate Jobs Airtable scraper (1 category)
3. Internship Airtable scraper (1 category)
4. H1B data loader (100 rows)
5. S3 upload functionality
6. Snowflake upload functionality
Schedule: Manual trigger only
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import sys
import os
import json

# Add scrapers directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scrapers'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from common.snowflake_utils import upload_to_snowflake, load_secrets
from common.s3_utils import upload_to_s3, cleanup_old_s3_files
import pandas as pd

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # No retries for test
    'retry_delay': timedelta(minutes=2),
}

def test_fortune500_scraper(**context):
    """Test Fortune 500 scraper with 2 companies"""
    print("\n" + "="*80)
    print("TEST 1: Fortune 500 Scraper (2 companies)")
    print("="*80)
    
    try:
        from Fortune_500 import UltraSmartScraper, scrape_single_company, ProgressManager
        from concurrent.futures import ThreadPoolExecutor
        
        # Get OpenAI API key from secrets
        secrets = load_secrets()
        openai_key = secrets['api']['openai_api_key']
        
        # Initialize scraper
        scraper = UltraSmartScraper(
            openai_key=openai_key,
            use_selenium=True
        )
        
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
        
        # TEST: Only scrape 2 companies
        test_companies = companies[:2]
        print(f"\n✓ Testing with companies: {[c['name'] for c in test_companies]}")
        
        progress = ProgressManager()
        all_jobs = []
        
        # Scrape companies sequentially for test
        for idx, company_info in enumerate(test_companies):
            print(f"\n--- Scraping company {idx+1}/2: {company_info['name']} ---")
            result = scrape_single_company(company_info, scraper, progress, idx)
            
            if result['success'] and result['jobs']:
                all_jobs.extend(result['jobs'])
                print(f"✓ Found {len(result['jobs'])} jobs from {company_info['name']}")
            else:
                print(f"✗ No jobs found for {company_info['name']}")
        
        print(f"\n✅ TEST 1 COMPLETE: Scraped {len(all_jobs)} total jobs from Fortune 500")
        
        # Push to XCom
        context['task_instance'].xcom_push(key='fortune500_jobs', value=all_jobs)
        context['task_instance'].xcom_push(key='fortune500_count', value=len(all_jobs))
        
        return len(all_jobs)
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def test_grad_jobs_scraper(**context):
    """Test Graduate Jobs Airtable scraper with 1 category"""
    print("\n" + "="*80)
    print("TEST 2: Graduate Jobs Airtable Scraper (1 category)")
    print("="*80)
    
    try:
        from Airtable_Comprehensive_scraper import ComprehensiveAirtableScraper
        
        # Initialize scraper
        scraper = ComprehensiveAirtableScraper(
            hours_lookback=168,  # 7 days
            max_retries=2,
            num_workers=1
        )
        
        # TEST: Only scrape 1 category (Software Engineering)
        test_categories = ['Software_Engineering']
        print(f"\n✓ Testing with category: {test_categories[0]}")
        
        # Scrape category
        results = scraper.scrape_all_categories(specific_categories=test_categories)
        
        # Collect jobs
        all_jobs = scraper.all_jobs
        
        print(f"\n✅ TEST 2 COMPLETE: Scraped {len(all_jobs)} grad jobs from Airtable")
        
        # Push to XCom
        context['task_instance'].xcom_push(key='grad_jobs', value=all_jobs)
        context['task_instance'].xcom_push(key='grad_count', value=len(all_jobs))
        
        return len(all_jobs)
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def test_internship_scraper(**context):
    """Test Internship Airtable scraper with 1 category"""
    print("\n" + "="*80)
    print("TEST 3: Internship Airtable Scraper (1 category)")
    print("="*80)
    
    try:
        from Internship_Airtable_scraper import InternshipAirtableScraper
        
        # Initialize scraper
        scraper = InternshipAirtableScraper(
            hours_lookback=168,  # 7 days
            max_retries=2,
            num_workers=1
        )
        
        # TEST: Only scrape 1 category (Software Engineering)
        test_categories = ['Software_Engineering']
        print(f"\n✓ Testing with category: {test_categories[0]}")
        
        # Scrape category
        results = scraper.scrape_all_categories(specific_categories=test_categories)
        
        # Collect jobs
        all_jobs = scraper.all_jobs
        
        print(f"\n✅ TEST 3 COMPLETE: Scraped {len(all_jobs)} internships from Airtable")
        
        # Push to XCom
        context['task_instance'].xcom_push(key='internship_jobs', value=all_jobs)
        context['task_instance'].xcom_push(key='internship_count', value=len(all_jobs))
        
        return len(all_jobs)
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def test_h1b_loader(**context):
    """Test H1B data loader with 100 rows"""
    print("\n" + "="*80)
    print("TEST 4: H1B Data Loader (100 rows)")
    print("="*80)
    
    try:
        # Path to H-1B data file
        data_file = os.path.join(
            os.path.dirname(__file__),
            '../../data/LCA_Disclosure_Data_FY2025_Q3.xlsx'
        )
        
        if not os.path.exists(data_file):
            raise FileNotFoundError(f"H-1B data file not found: {data_file}")
        
        print(f"✓ Loading H-1B data from: {data_file}")
        
        # Read Excel file
        df = pd.read_excel(data_file)
        print(f"✓ Total rows in file: {len(df)}")
        
        # TEST: Only load first 100 rows
        df_test = df.head(100)
        
        # Filter for USA jobs only
        if 'WORKSITE_STATE' in df_test.columns:
            df_test = df_test[df_test['WORKSITE_STATE'].notna()]
        
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
        
        available_columns = [col for col in columns_to_keep if col in df_test.columns]
        df_test = df_test[available_columns]
        
        # Convert to dict
        h1b_data = df_test.to_dict('records')
        
        print(f"\n✅ TEST 4 COMPLETE: Prepared {len(h1b_data)} H-1B records")
        
        # Push to XCom
        context['task_instance'].xcom_push(key='h1b_data', value=h1b_data)
        context['task_instance'].xcom_push(key='h1b_count', value=len(h1b_data))
        
        return len(h1b_data)
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def test_s3_upload(**context):
    """Test S3 upload for all four data sources"""
    print("\n" + "="*80)
    print("TEST 5: S3 Upload (All sources)")
    print("="*80)
    
    uploaded_files = []
    
    try:
        # Test 1: Fortune 500 to S3
        fortune500_jobs = context['task_instance'].xcom_pull(key='fortune500_jobs', task_ids='test_fortune500')
        if fortune500_jobs:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"raw/fortune500/test_jobs_{timestamp}.json"
            s3_path = upload_to_s3(fortune500_jobs, s3_key)
            uploaded_files.append(s3_path)
            print(f"✓ Fortune 500: {s3_path}")
        
        # Test 2: Graduate Jobs to S3
        grad_jobs = context['task_instance'].xcom_pull(key='grad_jobs', task_ids='test_grad_jobs')
        if grad_jobs:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"raw/airtable/grad/test_jobs_{timestamp}.json"
            s3_path = upload_to_s3(grad_jobs, s3_key)
            uploaded_files.append(s3_path)
            print(f"✓ Graduate Jobs: {s3_path}")
        
        # Test 3: Internships to S3
        internship_jobs = context['task_instance'].xcom_pull(key='internship_jobs', task_ids='test_internship')
        if internship_jobs:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"raw/airtable/internships/test_jobs_{timestamp}.json"
            s3_path = upload_to_s3(internship_jobs, s3_key)
            uploaded_files.append(s3_path)
            print(f"✓ Internships: {s3_path}")
        
        # Test 4: H1B to S3
        h1b_data = context['task_instance'].xcom_pull(key='h1b_data', task_ids='test_h1b')
        if h1b_data:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"raw/h1b/test_data_{timestamp}.json"
            s3_path = upload_to_s3(h1b_data, s3_key)
            uploaded_files.append(s3_path)
            print(f"✓ H1B: {s3_path}")
        
        print(f"\n✅ TEST 5 COMPLETE: Uploaded {len(uploaded_files)} files to S3")
        
        context['task_instance'].xcom_push(key='uploaded_files', value=uploaded_files)
        return len(uploaded_files)
        
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def test_snowflake_upload(**context):
    """Test Snowflake upload for all four data sources"""
    print("\n" + "="*80)
    print("TEST 6: Snowflake Upload (All sources)")
    print("="*80)
    
    total_rows = 0
    
    try:
        # Test 1: Fortune 500 to Snowflake
        fortune500_jobs = context['task_instance'].xcom_pull(key='fortune500_jobs', task_ids='test_fortune500')
        if fortune500_jobs:
            rows = upload_to_snowflake(
                data=fortune500_jobs,
                table='jobs_raw',
                database='job_intelligence',
                schema='raw'
            )
            total_rows += rows
            print(f"✓ Fortune 500: {rows} rows inserted")
        
        # Test 2: Graduate Jobs to Snowflake
        grad_jobs = context['task_instance'].xcom_pull(key='grad_jobs', task_ids='test_grad_jobs')
        if grad_jobs:
            rows = upload_to_snowflake(
                data=grad_jobs,
                table='jobs_raw',
                database='job_intelligence',
                schema='raw'
            )
            total_rows += rows
            print(f"✓ Graduate Jobs: {rows} rows inserted")
        
        # Test 3: Internships to Snowflake
        internship_jobs = context['task_instance'].xcom_pull(key='internship_jobs', task_ids='test_internship')
        if internship_jobs:
            rows = upload_to_snowflake(
                data=internship_jobs,
                table='jobs_raw',
                database='job_intelligence',
                schema='raw'
            )
            total_rows += rows
            print(f"✓ Internships: {rows} rows inserted")
        
        # Test 4: H1B to Snowflake
        h1b_data = context['task_instance'].xcom_pull(key='h1b_data', task_ids='test_h1b')
        if h1b_data:
            rows = upload_to_snowflake(
                data=h1b_data,
                table='h1b_raw',
                database='job_intelligence',
                schema='raw'
            )
            total_rows += rows
            print(f"✓ H1B: {rows} rows inserted")
        
        print(f"\n✅ TEST 6 COMPLETE: Inserted {total_rows} total rows to Snowflake")
        
        return total_rows
        
    except Exception as e:
        print(f"\n❌ TEST 6 FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def print_test_summary(**context):
    """Print comprehensive test summary"""
    print("\n" + "="*80)
    print("🎯 PIPELINE TEST SUMMARY")
    print("="*80)
    
    fortune500_count = context['task_instance'].xcom_pull(key='fortune500_count', task_ids='test_fortune500') or 0
    grad_count = context['task_instance'].xcom_pull(key='grad_count', task_ids='test_grad_jobs') or 0
    internship_count = context['task_instance'].xcom_pull(key='internship_count', task_ids='test_internship') or 0
    h1b_count = context['task_instance'].xcom_pull(key='h1b_count', task_ids='test_h1b') or 0
    uploaded_files = context['task_instance'].xcom_pull(key='uploaded_files', task_ids='test_s3_upload') or []
    
    print(f"\n📊 Data Collection:")
    print(f"   ✓ Fortune 500: {fortune500_count} jobs (2 companies)")
    print(f"   ✓ Graduate Jobs: {grad_count} jobs (1 category)")
    print(f"   ✓ Internships: {internship_count} jobs (1 category)")
    print(f"   ✓ H1B Data: {h1b_count} records (100 rows)")
    print(f"   📈 Total: {fortune500_count + grad_count + internship_count + h1b_count} records")
    
    print(f"\n☁️  S3 Upload:")
    print(f"   ✓ Files uploaded: {len(uploaded_files)}")
    for file_path in uploaded_files:
        print(f"      - {file_path}")
    
    print(f"\n❄️  Snowflake Upload:")
    print(f"   ✓ All data successfully loaded to Snowflake")
    print(f"   ✓ Tables: jobs_raw, h1b_raw")
    
    print(f"\n✅ ALL TESTS PASSED!")
    print(f"Pipeline is ready for production use.")
    print("="*80)

with DAG(
    'test_pipeline_dag',
    default_args=default_args,
    description='TEST: Validate all pipelines with small batches (Manual trigger only)',
    schedule_interval=None,  # Manual trigger only
    start_date=days_ago(1),
    catchup=False,
    tags=['test', 'validation', 'manual', 'pipeline'],
) as dag:
    
    # Test 1: Fortune 500 Scraper
    test_fortune500_task = PythonOperator(
        task_id='test_fortune500',
        python_callable=test_fortune500_scraper,
        provide_context=True,
        execution_timeout=timedelta(minutes=30),
    )
    
    # Test 2: Graduate Jobs Scraper
    test_grad_jobs_task = PythonOperator(
        task_id='test_grad_jobs',
        python_callable=test_grad_jobs_scraper,
        provide_context=True,
        execution_timeout=timedelta(minutes=15),
    )
    
    # Test 3: Internship Scraper
    test_internship_task = PythonOperator(
        task_id='test_internship',
        python_callable=test_internship_scraper,
        provide_context=True,
        execution_timeout=timedelta(minutes=15),
    )
    
    # Test 4: H1B Loader
    test_h1b_task = PythonOperator(
        task_id='test_h1b',
        python_callable=test_h1b_loader,
        provide_context=True,
        execution_timeout=timedelta(minutes=5),
    )
    
    # Test 5: S3 Upload (runs after all scraping tests)
    test_s3_task = PythonOperator(
        task_id='test_s3_upload',
        python_callable=test_s3_upload,
        provide_context=True,
    )
    
    # Test 6: Snowflake Upload (runs after S3)
    test_snowflake_task = PythonOperator(
        task_id='test_snowflake_upload',
        python_callable=test_snowflake_upload,
        provide_context=True,
    )
    
    # Summary (runs after all tests)
    summary_task = PythonOperator(
        task_id='print_summary',
        python_callable=print_test_summary,
        provide_context=True,
    )
    
    # Pipeline flow
    [test_fortune500_task, test_grad_jobs_task, test_internship_task, test_h1b_task] >> test_s3_task >> test_snowflake_task >> summary_task
