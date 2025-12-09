"""
Remove duplicate jobs from JOBS_PROCESSED table
Keeps the most recent version of each job based on scraped_at
"""
import json
import snowflake.connector
from pathlib import Path

# Load secrets
secrets_path = Path(__file__).parent.parent / 'secrets.json'
with open(secrets_path, 'r') as f:
    secrets = json.load(f)

sf = secrets['snowflake']
conn = snowflake.connector.connect(
    account=sf['account'],
    user=sf['user'],
    password=sf['password'],
    database='JOB_INTELLIGENCE',
    warehouse=sf['warehouse']
)

cursor = conn.cursor()

print('🧹 Deduplicating JOBS_PROCESSED...')
print('=' * 80)

# Find the table
cursor.execute("SHOW TABLES LIKE 'JOBS_PROCESSED' IN DATABASE JOB_INTELLIGENCE")
tables = cursor.fetchall()

for row in tables:
    schema_name = row[4]
    table_name = row[1]
    full_name = f'JOB_INTELLIGENCE.{schema_name}.{table_name}'
    
    print(f'\n📊 Table: {full_name}')
    
    # Count before
    cursor.execute(f'SELECT COUNT(*) FROM {full_name}')
    before = cursor.fetchone()[0]
    print(f'   Before: {before:,} rows')
    
    # Create backup
    print('   Creating backup...')
    cursor.execute(f'CREATE OR REPLACE TABLE {full_name}_BACKUP AS SELECT * FROM {full_name}')
    
    # Deduplicate (keep most recent by scraped_at)
    print('   Deduplicating...')
    cursor.execute(f'''
        CREATE OR REPLACE TABLE {full_name}_DEDUP AS
        SELECT * FROM (
            SELECT *, 
                   ROW_NUMBER() OVER (PARTITION BY job_id ORDER BY scraped_at DESC) as rn
            FROM {full_name}
        ) WHERE rn = 1
    ''')
    
    # Count after
    cursor.execute(f'SELECT COUNT(*) FROM {full_name}_DEDUP')
    after = cursor.fetchone()[0]
    
    # Replace original table
    print('   Replacing table...')
    cursor.execute(f'DROP TABLE {full_name}')
    cursor.execute(f'ALTER TABLE {full_name}_DEDUP RENAME TO {table_name}')
    
    print(f'\n   ✅ Complete!')
    print(f'   After:  {after:,} unique jobs')
    print(f'   Removed: {before - after:,} duplicates')
    print(f'\n✅ Frontend will now show {after:,} unique jobs!')

cursor.close()
conn.close()
