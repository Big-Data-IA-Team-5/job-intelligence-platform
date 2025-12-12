"""
DAG: Generate Job Embeddings
Automatically generates embeddings for new jobs in JOBS_RAW
Runs after scraper DAGs complete to keep EMBEDDED_JOBS up-to-date
Schedule: Every 6 hours
Duration: ~10-15 minutes per 1000 jobs
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pendulum

# Load code dependencies from GCS (Composer-compatible)
from gcs_loader import setup_code_dependencies, get_composer_bucket

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

def generate_embeddings(**context):
    """Generate embeddings for jobs missing from EMBEDDED_JOBS"""
    import sys
    import os
    
    # Load code from GCS
    bucket = get_composer_bucket()
    paths = setup_code_dependencies(bucket)
    
    print(f"🔍 Python path: {sys.path[:3]}")
    print(f"🔍 Current directory: {os.getcwd()}")
    
    import signal
    
    def timeout_handler(signum, frame):
        print("\n⏱️  TIMEOUT: Embedding generation exceeded 1-hour limit")
        raise TimeoutError("Embedding generation timeout after 1 hour")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(3600)
    
    try:
        from scripts.generate_embeddings import main
        
        print("=" * 80)
        print("🚀 STARTING EMBEDDING GENERATION")
        print("=" * 80)
        sys.stdout.flush()
        
        result = main()
        
        signal.alarm(0)
        
        print("\n" + "=" * 80)
        print("✅ EMBEDDING GENERATION COMPLETED")
        print("=" * 80)
        print(f"\n📊 Result: {result}")
        sys.stdout.flush()
        
        return result
    except TimeoutError as e:
        print(f"\n⏱️  TIMEOUT ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"📁 Available directories in {airflow_home}:")
        print(os.listdir(airflow_home))
        import traceback
        print(traceback.format_exc())
        raise

with DAG(
    'embedding_generator',
    default_args=default_args,
    description='Generate embeddings for new jobs automatically',
    schedule_interval='0 12 * * *',  # Run daily at 7:00 AM EST after all scrapers (12:00 UTC)
    start_date=pendulum.datetime(2024, 1, 1, 7, 0, tz="America/New_York"),
    catchup=False,
    tags=['embeddings', 'processing', 'automated'],
) as dag:
    
    generate_task = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_embeddings,
        provide_context=True,
    )
