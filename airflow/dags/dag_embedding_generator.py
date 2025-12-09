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
    
    # Add paths for script imports
    airflow_home = '/opt/airflow'
    sys.path.insert(0, airflow_home)
    sys.path.insert(0, os.path.join(airflow_home, 'scripts'))
    
    print(f"🔍 Python path: {sys.path[:3]}")
    print(f"🔍 Current directory: {os.getcwd()}")
    print(f"🔍 Scripts directory exists: {os.path.exists(os.path.join(airflow_home, 'scripts'))}")
    
    try:
        from scripts.generate_embeddings import main
        
        print("=" * 80)
        print("🚀 STARTING EMBEDDING GENERATION")
        print("=" * 80)
        
        # Run the embedding generation
        result = main()
        
        print("\n" + "=" * 80)
        print("✅ EMBEDDING GENERATION COMPLETED")
        print("=" * 80)
        print(f"\n📊 Result: {result}")
        
        return result
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print(f"📁 Available directories in {airflow_home}:")
        print(os.listdir(airflow_home))
        raise

with DAG(
    'embedding_generator',
    default_args=default_args,
    description='Generate embeddings for new jobs automatically',
    schedule_interval='0 */6 * * *',  # Every 6 hours (EST)
    start_date=pendulum.datetime(2024, 1, 1, tz="America/New_York"),
    catchup=False,
    tags=['embeddings', 'processing', 'automated'],
) as dag:
    
    generate_task = PythonOperator(
        task_id='generate_embeddings',
        python_callable=generate_embeddings,
        provide_context=True,
    )
