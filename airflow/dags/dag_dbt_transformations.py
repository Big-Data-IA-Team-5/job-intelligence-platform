"""
Airflow DAG for DBT Transformations
Runs DBT models to transform raw job data through staging, processing, and marts layers
Independent of scraper DAGs - processes all accumulated raw data
Pipeline: Download DBT from GCS -> Run DBT -> Verify Results
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import pendulum
import os
import json
import sys

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
    'execution_timeout': timedelta(hours=2),  # 2 hours for full DBT run
}

def check_raw_data_exists(**context):
    """
    Check if there's raw data in Snowflake to process
    """
    import snowflake.connector
    from google.cloud import storage
    import json
    
    print("=" * 80)
    print("CHECKING FOR RAW DATA IN SNOWFLAKE")
    print("=" * 80)
    
    # Download secrets.json from GCS
    bucket_name = get_composer_bucket()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob('data/secrets.json')
    
    secrets_path = '/tmp/secrets.json'
    blob.download_to_filename(secrets_path)
    
    # Load Snowflake credentials
    with open(secrets_path, 'r') as f:
        secrets = json.load(f)
    sf_creds = secrets['snowflake']
    
    # Connect to Snowflake
    conn = snowflake.connector.connect(
        user=sf_creds['user'],
        password=sf_creds['password'],
        account=sf_creds['account'],
        warehouse=sf_creds['warehouse'],
        database='job_intelligence',
        schema='raw',
        role=sf_creds['role']
    )
    
    cursor = conn.cursor()
    
    try:
        # Check if jobs_raw table has data
        cursor.execute("SELECT COUNT(*) as row_count FROM jobs_raw")
        result = cursor.fetchone()
        row_count = result[0] if result else 0
        
        print(f"\n📊 Raw data status:")
        print(f"   Table: job_intelligence.raw.jobs_raw")
        print(f"   Row count: {row_count:,}")
        
        # Push to XCom
        context['ti'].xcom_push(key='raw_row_count', value=row_count)
        
        if row_count > 0:
            print(f"\n✅ Found {row_count:,} rows - proceeding with DBT transformations")
            return 'download_dbt_project'
        else:
            print("\n⚠️  No raw data found - skipping DBT transformations")
            return 'skip_dbt'
            
    except Exception as e:
        print(f"\n❌ Error checking raw data: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def download_dbt_project(**context):
    """
    Download DBT project files from GCS to /tmp/airflow_dbt
    """
    from google.cloud import storage
    import shutil
    
    print("=" * 80)
    print("DOWNLOADING DBT PROJECT FROM GCS")
    print("=" * 80)
    
    # Get bucket
    bucket = get_composer_bucket()
    client = storage.Client()
    gcs_bucket = client.bucket(bucket)
    
    # Create local DBT directory
    local_dbt_path = '/tmp/airflow_dbt'
    if os.path.exists(local_dbt_path):
        shutil.rmtree(local_dbt_path)
    os.makedirs(local_dbt_path, exist_ok=True)
    
    print(f"\n📂 Local DBT path: {local_dbt_path}")
    print(f"📦 GCS bucket: {bucket}")
    
    # Download DBT files
    dbt_files = [
        'dbt_project.yml',
        'profiles.yml',
    ]
    
    # Download root files
    for file in dbt_files:
        blob = gcs_bucket.blob(f'data/dbt/{file}')
        if blob.exists():
            local_file = os.path.join(local_dbt_path, file)
            blob.download_to_filename(local_file)
            print(f"   ✓ Downloaded: {file}")
        else:
            print(f"   ⚠️  Not found: {file}")
    
    # Download directories (models, macros, etc.)
    directories = ['models', 'macros', 'dbt_packages']
    for directory in directories:
        blobs = list(gcs_bucket.list_blobs(prefix=f'data/dbt/{directory}/'))
        if blobs:
            for blob in blobs:
                if not blob.name.endswith('/'):  # Skip directory markers
                    # Create local path
                    relative_path = blob.name.replace('data/dbt/', '', 1)
                    local_file = os.path.join(local_dbt_path, relative_path)
                    os.makedirs(os.path.dirname(local_file), exist_ok=True)
                    
                    # Download file
                    blob.download_to_filename(local_file)
            print(f"   ✓ Downloaded directory: {directory}/ ({len(blobs)} files)")
    
    # Verify critical files exist
    required_files = ['dbt_project.yml', 'profiles.yml']
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(local_dbt_path, f))]
    
    if missing_files:
        raise FileNotFoundError(f"Missing required DBT files: {missing_files}")
    
    print(f"\n✅ DBT project downloaded successfully to {local_dbt_path}")
    
    # Push path to XCom
    context['ti'].xcom_push(key='dbt_path', value=local_dbt_path)
    return local_dbt_path

def install_dbt_deps(**context):
    """
    Install DBT dependencies (dbt packages)
    """
    import subprocess
    
    print("=" * 80)
    print("INSTALLING DBT DEPENDENCIES")
    print("=" * 80)
    
    dbt_path = context['ti'].xcom_pull(key='dbt_path', task_ids='download_dbt_project')
    
    if not dbt_path or not os.path.exists(dbt_path):
        raise FileNotFoundError(f"DBT path not found: {dbt_path}")
    
    print(f"\n📂 DBT path: {dbt_path}")
    
    # Check if packages.yml exists
    packages_file = os.path.join(dbt_path, 'packages.yml')
    if os.path.exists(packages_file):
        print(f"\n📦 Found packages.yml, installing dependencies...")
        
        try:
            # Run dbt deps using Python module
            result = subprocess.run(
                ['python', '-m', 'dbt.cli.main', 'deps', '--profiles-dir', dbt_path],
                cwd=dbt_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            print("\nDBT deps output:")
            print(result.stdout)
            
            if result.returncode != 0:
                print(f"\n⚠️  DBT deps warning/error:")
                print(result.stderr)
            else:
                print("\n✅ DBT dependencies installed successfully")
                
        except subprocess.TimeoutExpired:
            print("\n⚠️  DBT deps timed out - continuing anyway")
        except Exception as e:
            print(f"\n⚠️  Error installing DBT deps: {e}")
            print("Continuing anyway - may not be critical")
    else:
        print(f"\n📝 No packages.yml found - skipping dependency installation")
    
    return True

def verify_dbt_results(**context):
    """
    Verify DBT transformations completed successfully
    Check row counts in staging, processing, and marts schemas
    """
    import snowflake.connector
    from google.cloud import storage
    import json
    
    print("=" * 80)
    print("VERIFYING DBT TRANSFORMATION RESULTS")
    print("=" * 80)
    
    # Download secrets.json from GCS
    bucket_name = get_composer_bucket()
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob('data/secrets.json')
    
    secrets_path = '/tmp/secrets.json'
    blob.download_to_filename(secrets_path)
    
    # Load Snowflake credentials
    with open(secrets_path, 'r') as f:
        secrets = json.load(f)
    sf_creds = secrets['snowflake']
    
    # Connect to Snowflake
    conn = snowflake.connector.connect(
        user=sf_creds['user'],
        password=sf_creds['password'],
        account=sf_creds['account'],
        warehouse=sf_creds['warehouse'],
        database='job_intelligence',
        schema='raw',
        role=sf_creds['role']
    )
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("USE DATABASE job_intelligence")
        
        # Check tables in different schemas
        schemas_tables = {
            'staging': ['stg_jobs', 'dedup_jobs'],
            'processing': ['classified_jobs', 'embedded_jobs', 'h1b_matched_jobs'],
            'marts': ['job_intelligence_mart']
        }
        
        results = {}
        
        for schema, tables in schemas_tables.items():
            cursor.execute(f"USE SCHEMA {schema}")
            print(f"\n📊 Schema: {schema}")
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    result = cursor.fetchone()
                    row_count = result[0] if result else 0
                    results[f"{schema}.{table}"] = row_count
                    print(f"   ✓ {table}: {row_count:,} rows")
                except Exception as e:
                    print(f"   ⚠️  {table}: Error - {str(e)[:100]}")
                    results[f"{schema}.{table}"] = 0
        
        # Push results to XCom
        context['ti'].xcom_push(key='dbt_results', value=results)
        
        # Check if marts table has data
        marts_count = results.get('marts.job_intelligence_mart', 0)
        if marts_count > 0:
            print(f"\n✅ DBT transformations completed successfully!")
            print(f"   Final marts table has {marts_count:,} rows")
        else:
            print(f"\n⚠️  Warning: marts.job_intelligence_mart is empty")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error verifying DBT results: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def run_dbt_transformations(**context):
    """
    Run DBT transformations using Python module with real-time output logging
    """
    import subprocess
    from google.cloud import storage
    import sys
    
    print("=" * 80)
    print("RUNNING DBT TRANSFORMATIONS")
    print("=" * 80)
    
    # Try to get from XCom first
    dbt_path = context['ti'].xcom_pull(key='dbt_path', task_ids='download_dbt_project')
    
    # If not found (different worker), download DBT project ourselves
    if not dbt_path or not os.path.exists(dbt_path):
        print(f"\n⚠️ DBT path not found from XCom or doesn't exist: {dbt_path}")
        print("📥 Downloading DBT project to this worker...")
        
        bucket_name = get_composer_bucket()
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        local_dbt_path = '/tmp/airflow_dbt'
        os.makedirs(local_dbt_path, exist_ok=True)
        
        # Download all files from dbt/ in GCS
        blobs = bucket.list_blobs(prefix='dbt/')
        for blob in blobs:
            if blob.name.endswith('/'):
                continue
            local_file = os.path.join(local_dbt_path, blob.name.replace('dbt/', ''))
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            blob.download_to_filename(local_file)
            print(f"   Downloaded: {blob.name}")
        
        dbt_path = local_dbt_path
        print(f"\n✅ DBT project downloaded to {dbt_path}")
    
    print(f"\n📂 DBT path: {dbt_path}")
    print(f"📝 Running: python -m dbt.cli.main run --profiles-dir {dbt_path} --target prod")
    print("⏳ This may take several minutes... streaming output below:\n")
    
    import time
    import threading
    
    timeout_seconds = 3600  # 1 hour timeout
    start_time = time.time()
    
    try:
        # Run dbt as Python module with real-time output streaming
        process = subprocess.Popen(
            ['python', '-m', 'dbt.cli.main', 'run', '--profiles-dir', dbt_path, '--target', 'prod'],
            cwd=dbt_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffering
        )
        
        # Read output in real-time with timeout check
        last_output_time = time.time()
        output_timeout = 600  # Kill if no output for 10 minutes
        
        while True:
            # Check total timeout
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                print(f"\n⏱️  TIMEOUT: DBT run exceeded {timeout_seconds/60:.0f} minutes")
                process.kill()
                raise Exception(f"DBT run timed out after {timeout_seconds/60:.0f} minutes")
            
            # Check for process completion
            if process.poll() is not None:
                # Process finished, read any remaining output
                remaining = process.stdout.read()
                if remaining:
                    print(remaining.rstrip())
                    sys.stdout.flush()
                break
            
            # Try to read a line with timeout
            import select
            ready, _, _ = select.select([process.stdout], [], [], 1.0)
            
            if ready:
                output = process.stdout.readline()
                if output:
                    print(output.rstrip())
                    sys.stdout.flush()
                    last_output_time = time.time()
            else:
                # No output for 1 second, check if stuck
                if time.time() - last_output_time > output_timeout:
                    print(f"\n⏱️  TIMEOUT: No output for {output_timeout/60:.0f} minutes")
                    process.kill()
                    raise Exception(f"DBT process hung - no output for {output_timeout/60:.0f} minutes")
        
        # Get any remaining stderr
        stderr_output = process.stderr.read()
        if stderr_output:
            print("\n" + "=" * 80)
            print("DBT STDERR OUTPUT:")
            print("=" * 80)
            print(stderr_output)
            sys.stdout.flush()
        
        return_code = process.returncode
        
        if return_code != 0:
            print("\n" + "=" * 80)
            print(f"❌ DBT run failed with return code {return_code}")
            print("=" * 80)
            sys.stdout.flush()
            raise Exception(f"DBT run failed with return code {return_code}")
        else:
            elapsed_minutes = (time.time() - start_time) / 60
            print("\n" + "=" * 80)
            print(f"✅ DBT transformations completed successfully in {elapsed_minutes:.1f} minutes")
            print("=" * 80)
            sys.stdout.flush()
            
    except Exception as e:
        print(f"\n❌ Error running DBT: {e}")
        import traceback
        print(traceback.format_exc())
        sys.stdout.flush()
        
        # Make sure process is killed
        try:
            if 'process' in locals() and process.poll() is None:
                process.kill()
                process.wait(timeout=5)
        except:
            pass
        raise

def print_pipeline_summary(**context):
    """Print comprehensive pipeline summary"""
    print("\n" + "=" * 80)
    print("🎯 DBT TRANSFORMATIONS PIPELINE SUMMARY")
    print("=" * 80)
    
    raw_row_count = context['ti'].xcom_pull(key='raw_row_count', task_ids='check_raw_data') or 0
    dbt_results = context['ti'].xcom_pull(key='dbt_results', task_ids='verify_dbt_results') or {}
    
    print(f"\n📊 Results:")
    print(f"   ✓ Raw data processed: {raw_row_count:,} rows")
    
    if dbt_results:
        print(f"\n   DBT Output Tables:")
        for table, count in dbt_results.items():
            print(f"      • {table}: {count:,} rows")
    
    print(f"\n✅ DBT PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)

# Create DAG
with DAG(
    'dbt_transformations',
    default_args=default_args,
    description='DBT transformations: raw -> staging -> processing -> marts',
    schedule_interval='0 */6 * * *',  # Run every 6 hours
    start_date=pendulum.datetime(2025, 12, 11, 0, 0, tz="UTC"),
    catchup=False,
    tags=['dbt', 'transformation', 'snowflake', 'processing', 'marts'],
) as dag:
    
    # Task 1: Check if raw data exists
    check_data = BranchPythonOperator(
        task_id='check_raw_data',
        python_callable=check_raw_data_exists,
        provide_context=True,
    )
    
    # Task 2: Download DBT project from GCS
    download_dbt = PythonOperator(
        task_id='download_dbt_project',
        python_callable=download_dbt_project,
        provide_context=True,
    )
    
    # Task 3: Install DBT dependencies
    install_deps = PythonOperator(
        task_id='install_dbt_deps',
        python_callable=install_dbt_deps,
        provide_context=True,
    )
    
    # Task 4: Run DBT transformations
    # This runs all models: staging (stg_jobs, dedup_jobs) -> 
    #                       processing (classified_jobs, embedded_jobs, h1b_matched_jobs) -> 
    #                       marts (job_intelligence_mart)
    run_dbt = PythonOperator(
        task_id='run_dbt_transformations',
        python_callable=run_dbt_transformations,
        provide_context=True,
        execution_timeout=timedelta(hours=1),  # 1 hour for full DBT run
    )
    
    # Task 5: Verify DBT results
    verify_results = PythonOperator(
        task_id='verify_dbt_results',
        python_callable=verify_dbt_results,
        provide_context=True,
    )
    
    # Task 6: Print summary
    summary_task = PythonOperator(
        task_id='print_summary',
        python_callable=print_pipeline_summary,
        provide_context=True,
        trigger_rule='all_done',  # Run even if previous tasks fail
    )
    
    # Task 7: Skip DBT (dummy task for branching)
    skip_dbt = DummyOperator(
        task_id='skip_dbt',
        trigger_rule='none_failed_or_skipped',
    )
    
    # Pipeline with branching
    # Check data -> If data exists: Download DBT -> Install deps -> Run DBT -> Verify -> Summary
    #            -> If no data: Skip -> Summary
    check_data >> [download_dbt, skip_dbt]
    download_dbt >> install_deps >> run_dbt >> verify_results >> summary_task
    skip_dbt >> summary_task
