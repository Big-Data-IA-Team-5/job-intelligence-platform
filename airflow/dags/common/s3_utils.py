"""S3 utility functions for DAGs"""
import boto3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

def load_secrets():
    """Load secrets from secrets.json file"""
    # Try Composer/GCS download location first (from setup_code_dependencies)
    composer_path = Path('/tmp/airflow_code/secrets.json')
    # Then Docker mount location
    docker_path = Path('/opt/airflow/secrets/secrets.json')
    docker_path_alt = Path('/opt/airflow/secrets.json')
    
    if composer_path.exists():
        secrets_path = composer_path
    elif docker_path.exists():
        secrets_path = docker_path
    elif docker_path_alt.exists():
        secrets_path = docker_path_alt
    else:
        # Local development: look in project root
        current_dir = Path(__file__).resolve()
        project_root = current_dir.parent.parent.parent.parent
        secrets_path = project_root / 'secrets.json'
    
    if not secrets_path.exists():
        raise FileNotFoundError(f"secrets.json not found at {secrets_path}")
    
    with open(secrets_path, 'r') as f:
        return json.load(f)

def get_s3_client():
    """Get S3 client from secrets.json"""
    secrets = load_secrets()
    aws_config = secrets['aws']
    
    return boto3.client(
        's3',
        aws_access_key_id=aws_config['access_key_id'],
        aws_secret_access_key=aws_config['secret_access_key'],
        region_name=aws_config['region']
    )

def upload_to_s3(
    data: List[Dict[str, Any]],
    s3_key: str,
    bucket_name: str = None
) -> str:
    """
    Upload data to S3 as JSON
    
    Args:
        data: List of dictionaries to upload
        s3_key: S3 object key (path)
        bucket_name: S3 bucket name (from secrets if not provided)
        
    Returns:
        S3 path (s3://bucket/key)
    """
    if bucket_name is None:
        secrets = load_secrets()
        bucket_name = secrets['aws']['s3_bucket']
    
    s3_client = get_s3_client()
    
    # Convert data to JSON string
    json_data = json.dumps(data, indent=2, default=str)
    
    # Upload to S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json_data.encode('utf-8'),
        ContentType='application/json'
    )
    
    s3_path = f"s3://{bucket_name}/{s3_key}"
    print(f"Uploaded {len(data)} records to {s3_path}")
    
    return s3_path

def download_from_s3(s3_key: str, bucket_name: str = None) -> List[Dict[str, Any]]:
    """
    Download JSON data from S3
    
    Args:
        s3_key: S3 object key (path)
        bucket_name: S3 bucket name (from secrets if not provided)
        
    Returns:
        List of dictionaries
    """
    if bucket_name is None:
        secrets = load_secrets()
        bucket_name = secrets['aws']['s3_bucket']
    
    s3_client = get_s3_client()
    
    # Download from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
    json_data = response['Body'].read().decode('utf-8')
    
    data = json.loads(json_data)
    print(f"Downloaded {len(data)} records from s3://{bucket_name}/{s3_key}")
    
    return data

def cleanup_old_s3_files(prefix: str, days_to_keep: int = 30, bucket_name: str = None):
    """
    Delete S3 files older than specified days
    
    Args:
        prefix: S3 key prefix (folder path)
        days_to_keep: Number of days to retain files (default: 30)
        bucket_name: S3 bucket name (from secrets if not provided)
        
    Returns:
        Number of files deleted
    """
    if bucket_name is None:
        secrets = load_secrets()
        bucket_name = secrets['aws']['s3_bucket']
    
    s3_client = get_s3_client()
    
    # List all objects with the prefix
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    
    if 'Contents' not in response:
        print(f"No files found with prefix: {prefix}")
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    files_deleted = 0
    
    for obj in response['Contents']:
        last_modified = obj['LastModified'].replace(tzinfo=None)
        
        if last_modified < cutoff_date:
            s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
            print(f"Deleted old file: {obj['Key']} (modified: {last_modified})")
            files_deleted += 1
    
    print(f"Cleaned up {files_deleted} files older than {days_to_keep} days from {prefix}")
    return files_deleted
