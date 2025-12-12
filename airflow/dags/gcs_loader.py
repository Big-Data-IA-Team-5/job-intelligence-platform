"""
GCS Code Loader - Download Python modules from Composer's GCS bucket at runtime
This allows scrapers and scripts to be stored in GCS and loaded dynamically
"""
import os
import sys
from pathlib import Path
from google.cloud import storage

def download_from_gcs(bucket_name: str, source_path: str, dest_path: str):
    """Download files from GCS to local path"""
    client = storage.Client()
    bucket = client.bucket(bucket_name.replace('gs://', ''))
    
    blobs = bucket.list_blobs(prefix=source_path)
    
    for blob in blobs:
        if blob.name.endswith('/'):
            continue
            
        # Create local path
        relative_path = blob.name.replace(source_path, '').lstrip('/')
        local_file = Path(dest_path) / relative_path
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Download file
        blob.download_to_filename(str(local_file))
        print(f"✅ Downloaded: {blob.name} -> {local_file}")

def setup_code_dependencies(gcs_bucket: str, local_base: str = '/tmp/airflow_code'):
    """
    Download scrapers and scripts from GCS to local filesystem
    Add them to Python path for imports
    
    Args:
        gcs_bucket: GCS bucket path (e.g., 'gs://us-central1-job-intel-abc123-bucket')
        local_base: Local directory to download code to
    
    Returns:
        Dictionary with paths to downloaded modules
    """
    local_base = Path(local_base)
    local_base.mkdir(parents=True, exist_ok=True)
    
    paths = {}
    
    # Download scrapers
    scrapers_local = local_base / 'scrapers'
    print(f"📦 Downloading scrapers from {gcs_bucket}/data/scrapers...")
    download_from_gcs(gcs_bucket, 'data/scrapers', str(scrapers_local))
    sys.path.insert(0, str(local_base))
    paths['scrapers'] = str(scrapers_local)
    
    # Download scripts
    scripts_local = local_base / 'scripts'
    print(f"📦 Downloading scripts from {gcs_bucket}/data/scripts...")
    download_from_gcs(gcs_bucket, 'data/scripts', str(scripts_local))
    sys.path.insert(0, str(scripts_local))
    paths['scripts'] = str(scripts_local)
    
    # Download secrets if exists
    secrets_local = local_base / 'secrets.json'
    try:
        print(f"🔐 Downloading secrets from {gcs_bucket}/data/secrets.json...")
        client = storage.Client()
        bucket = client.bucket(gcs_bucket.replace('gs://', ''))
        blob = bucket.blob('data/secrets.json')
        blob.download_to_filename(str(secrets_local))
        paths['secrets'] = str(secrets_local)
        print(f"✅ Secrets downloaded to {secrets_local}")
    except Exception as e:
        print(f"⚠️  Could not download secrets: {e}")
    
    print(f"\n✅ All code dependencies loaded!")
    print(f"   Python path updated with: {local_base}")
    
    return paths

def get_composer_bucket():
    """Get the Composer GCS bucket from environment metadata"""
    # In Composer, this is available via environment variable
    bucket = os.getenv('GCS_BUCKET')
    if bucket:
        print(f"✅ Using GCS_BUCKET env var: {bucket}")
        return bucket
    
    # Fallback: derive from DAGS folder path
    dags_folder = os.getenv('AIRFLOW__CORE__DAGS_FOLDER', '')
    print(f"🔍 AIRFLOW__CORE__DAGS_FOLDER: {dags_folder}")
    
    if dags_folder and 'gs://' in dags_folder:
        # Extract bucket from gs://bucket-name/dags
        bucket = dags_folder.split('/dags')[0]
        print(f"✅ Extracted bucket from DAGS_FOLDER: {bucket}")
        return bucket
    
    # Fallback: hardcoded bucket for known Composer environment
    fallback_bucket = 'gs://us-central1-job-intel-airfl-d2b0ae78-bucket'
    print(f"⚠️  Using fallback bucket: {fallback_bucket}")
    return fallback_bucket
