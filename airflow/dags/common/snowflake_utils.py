"""Snowflake utility functions for DAGs"""
import snowflake.connector
import os
import json
import math
from typing import List, Dict, Any
from pathlib import Path

def clean_nan_values(value):
    """Convert NaN/None to None for Snowflake compatibility"""
    if value is None:
        return None
    # Check for NaN (works for both float NaN and numpy NaN)
    if isinstance(value, float) and math.isnan(value):
        return None
    # Check for string 'nan' or 'NaN'
    if isinstance(value, str) and value.lower() == 'nan':
        return None
    return value

def format_value(value):
    """Format value for SQL INSERT statement"""
    value = clean_nan_values(value)
    if value is None:
        return 'NULL'
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, bool):
        return 'TRUE' if value else 'FALSE'
    else:
        # Escape single quotes for SQL
        return f"'{str(value).replace(chr(39), chr(39)+chr(39))}'"

def load_secrets():
    """Load secrets from secrets.json file"""
    # Try Docker mount locations first, then local development path
    docker_path = Path('/opt/airflow/secrets/secrets.json')
    docker_path_alt = Path('/opt/airflow/secrets.json')
    
    if docker_path.exists():
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

def get_snowflake_connection():
    """Get Snowflake connection from secrets.json"""
    secrets = load_secrets()
    sf_config = secrets['snowflake']
    
    return snowflake.connector.connect(
        user=sf_config['user'],
        password=sf_config['password'],
        account=sf_config['account'],
        warehouse=sf_config['warehouse'],
        database=sf_config['database'],
        schema=sf_config['schema'],
        role=sf_config['role']
    )

def upload_to_snowflake(
    data: List[Dict[str, Any]],
    table: str,
    database: str = None,
    schema: str = None
) -> int:
    """
    Upload data to Snowflake table (jobs_raw or h1b_raw)
    
    Args:
        data: List of dictionaries containing job or H1B data
        table: Target table name (jobs_raw or h1b_raw)
        database: Database name
        schema: Schema name
        
    Returns:
        Number of rows inserted
    """
    if not data:
        print("No data to upload")
        return 0
    
    # Load defaults from secrets if not provided
    if database is None or schema is None:
        secrets = load_secrets()
        if database is None:
            database = secrets['snowflake']['database']
        if schema is None:
            schema = secrets['snowflake']['schema']
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    try:
        # Use the specified database and schema
        cursor.execute(f"USE DATABASE {database}")
        cursor.execute(f"USE SCHEMA {schema}")
        
        # Insert data based on table type
        rows_inserted = 0
        
        if table.lower() == 'h1b_raw':
            # H1B-specific insert - BATCH INSERT for performance
            insert_query = f"""
            INSERT INTO {table} (
                case_number, employer_name, job_title, soc_title,
                worksite_city, worksite_state, 
                wage_rate_of_pay_from, wage_rate_of_pay_to, wage_unit_of_pay,
                h1b_dependent, willful_violator
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            # Prepare all values for batch insert
            batch_values = []
            for record in data:
                values = (
                    clean_nan_values(record.get('CASE_NUMBER')),
                    clean_nan_values(record.get('EMPLOYER_NAME')),
                    clean_nan_values(record.get('JOB_TITLE')),
                    clean_nan_values(record.get('SOC_TITLE')),
                    clean_nan_values(record.get('WORKSITE_CITY')),
                    clean_nan_values(record.get('WORKSITE_STATE')),
                    clean_nan_values(record.get('WAGE_RATE_OF_PAY_FROM')),
                    clean_nan_values(record.get('WAGE_RATE_OF_PAY_TO')),
                    clean_nan_values(record.get('WAGE_UNIT_OF_PAY')),
                    clean_nan_values(record.get('H1B_DEPENDENT')),
                    clean_nan_values(record.get('WILLFUL_VIOLATOR'))
                )
                batch_values.append(values)
            
            # Execute batch insert - all rows in single transaction
            cursor.executemany(insert_query, batch_values)
            rows_inserted = len(batch_values)
            print(f"✅ Batch inserted {rows_inserted} H1B records in single transaction")
        else:
            # Jobs table insert - BATCH INSERT for performance (industry standard)
            insert_query = f"""
            INSERT INTO {table} (
                job_id, url, title, company, location, description, snippet,
                salary_min, salary_max, salary_text, job_type, posted_date,
                work_model, department, company_size, qualifications, 
                h1b_sponsored, is_new_grad, category,
                scraped_at, source, raw_json
            )
            SELECT 
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, 
                CURRENT_TIMESTAMP(), 
                %s, 
                PARSE_JSON(%s)
            """
            
            # Batch insert in chunks of 1000 rows (Snowflake best practice)
            batch_size = 1000
            rows_inserted = 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                
                # Build VALUES clause for batch
                values_list = []
                for record in batch:
                    raw_json_str = json.dumps(record).replace("'", "''")
                    values_list.append(f"""(
                        {format_value(record.get('job_id'))},
                        {format_value(record.get('url'))},
                        {format_value(record.get('title'))},
                        {format_value(record.get('company'))},
                        {format_value(record.get('location'))},
                        {format_value(record.get('description'))},
                        {format_value(record.get('snippet'))},
                        {format_value(record.get('salary_min'))},
                        {format_value(record.get('salary_max'))},
                        {format_value(record.get('salary_text'))},
                        {format_value(record.get('job_type'))},
                        {format_value(record.get('posted_date'))},
                        {format_value(record.get('work_model'))},
                        {format_value(record.get('department'))},
                        {format_value(record.get('company_size'))},
                        {format_value(record.get('qualifications'))},
                        {format_value(record.get('h1b_sponsored'))},
                        {format_value(record.get('is_new_grad'))},
                        {format_value(record.get('category'))},
                        {format_value(record.get('source', 'unknown'))},
                        '{raw_json_str}'
                    )""")
                
                # Execute batch INSERT with VALUES
                batch_insert_query = insert_query.replace('VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                                                         f"VALUES {', '.join(values_list)}")
                cursor.execute(batch_insert_query)
                rows_inserted += len(batch)
                print(f"✅ Batch inserted {len(batch)} jobs (total: {rows_inserted}/{len(data)})")
        
        conn.commit()
        print(f"Successfully inserted {rows_inserted} rows into {database}.{schema}.{table}")
        
        return rows_inserted
        
    except Exception as e:
        conn.rollback()
        print(f"Error uploading to Snowflake: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def copy_from_s3_to_snowflake(
    s3_path: str,
    table: str,
    database: str = None,
    schema: str = None
) -> int:
    """
    Tell Snowflake to COPY data from S3 into a table
    Snowflake pulls from S3 directly (not Airflow pushing to Snowflake)
    
    Args:
        s3_path: Full S3 path (s3://bucket/path/to/file.json)
        table: Target table name
        database: Database name
        schema: Schema name
        
    Returns:
        Number of rows loaded
    """
    # Load defaults and AWS credentials from secrets
    secrets = load_secrets()
    if database is None:
        database = secrets['snowflake']['database']
    if schema is None:
        schema = secrets['snowflake']['schema']
    
    aws_config = secrets['aws']
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"USE DATABASE {database}")
        cursor.execute(f"USE SCHEMA {schema}")
        
        # COPY INTO command - Snowflake pulls from S3
        copy_query = f"""
        COPY INTO {table} (JOB_DATA, SCRAPED_AT, SOURCE)
        FROM (
            SELECT 
                $1,
                CURRENT_TIMESTAMP(),
                PARSE_JSON($1):source::STRING
            FROM @~/staged_data
        )
        FILE_FORMAT = (TYPE = 'JSON')
        """
        
        # First, stage the file from S3 (Snowflake internal stage)
        stage_query = f"""
        PUT '{s3_path}' @~/staged_data
        AUTO_COMPRESS = FALSE
        """
        
        print(f"Telling Snowflake to load from S3: {s3_path}")
        
        # Alternative: Use external stage with AWS credentials
        # This is the proper way - Snowflake pulls directly from S3
        copy_with_credentials = f"""
        COPY INTO {table} (JOB_DATA, SCRAPED_AT, SOURCE)
        FROM (
            SELECT 
                PARSE_JSON($1),
                CURRENT_TIMESTAMP(),
                PARSE_JSON($1):source::STRING
            FROM '{s3_path}'
        )
        CREDENTIALS = (
            AWS_KEY_ID = '{aws_config['access_key_id']}'
            AWS_SECRET_KEY = '{aws_config['secret_access_key']}'
        )
        FILE_FORMAT = (TYPE = 'JSON')
        ON_ERROR = 'CONTINUE'
        """
        
        cursor.execute(copy_with_credentials)
        
        # Get row count
        result = cursor.fetchone()
        rows_loaded = result[0] if result else 0
        
        conn.commit()
        print(f"✅ Snowflake loaded {rows_loaded} rows from S3")
        
        return rows_loaded
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error telling Snowflake to load from S3: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()

def execute_query(query: str, database: str = None, schema: str = None):
    """Execute a SQL query in Snowflake"""
    # Load defaults from secrets if not provided
    if database is None or schema is None:
        secrets = load_secrets()
        if database is None:
            database = secrets['snowflake']['database']
        if schema is None:
            schema = secrets['snowflake']['schema']
    
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(f"USE DATABASE {database}")
        cursor.execute(f"USE SCHEMA {schema}")
        cursor.execute(query)
        conn.commit()
        
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
