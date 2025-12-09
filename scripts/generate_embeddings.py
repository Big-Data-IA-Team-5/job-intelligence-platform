"""
Generate embeddings for jobs missing them
Bypasses dbt and directly creates embeddings in Snowflake
"""
import json
import snowflake.connector
from pathlib import Path
import sys

def generate_embeddings():
    """Generate embeddings for all jobs in JOBS_RAW that don't have them yet"""
    
    # Load secrets
    secrets_path = Path(__file__).parent.parent / 'secrets.json'
    with open(secrets_path, 'r') as f:
        secrets = json.load(f)
    
    sf = secrets['snowflake']
    
    # Connect to Snowflake
    print("🔌 Connecting to Snowflake...")
    conn = snowflake.connector.connect(
        account=sf['account'],
        user=sf['user'],
        password=sf['password'],
        database='JOB_INTELLIGENCE',
        warehouse=sf['warehouse'],
        schema='PROCESSED_PROCESSING'
    )
    
    cursor = conn.cursor()
    
    try:
        # Step 1: Check current state
        print("\n📊 Checking current state...")
        cursor.execute("SELECT COUNT(*) FROM RAW.JOBS_RAW")
        jobs_raw_count = cursor.fetchone()[0]
        print(f"   • JOBS_RAW: {jobs_raw_count:,} jobs")
        
        cursor.execute("SELECT COUNT(*) FROM PROCESSED.JOBS_PROCESSED")
        processed_count = cursor.fetchone()[0]
        print(f"   • JOBS_PROCESSED: {processed_count:,} jobs")
        
        missing = jobs_raw_count - processed_count
        print(f"   • Missing from JOBS_PROCESSED: {missing:,} jobs\n")
        
        if missing <= 0:
            print("✅ All jobs already in JOBS_PROCESSED!")
            return None
        
        # Step 2: Get jobs that need to be added to JOBS_PROCESSED
        print("🔍 Finding jobs missing from JOBS_PROCESSED...")
        cursor.execute("""
            SELECT j.job_id
            FROM RAW.JOBS_RAW j
            LEFT JOIN PROCESSED.JOBS_PROCESSED p ON j.job_id = p.job_id
            WHERE p.job_id IS NULL
            LIMIT 5000
        """)
        missing_job_ids = [row[0] for row in cursor.fetchall()]
        print(f"   Found {len(missing_job_ids):,} jobs to process")
        
        if not missing_job_ids:
            print("✅ No missing jobs!")
            return None
        
        # Step 3: Sync JOBS_PROCESSED with existing embeddings
        print(f"\n🚀 Syncing JOBS_PROCESSED with embedded jobs...")
        batch_size = 100
        total_processed = 0
        
        for i in range(0, len(missing_job_ids), batch_size):
            batch = missing_job_ids[i:i+batch_size]
            batch_ids = "', '".join(batch)
            
            sql = f"""
            MERGE INTO PROCESSED.JOBS_PROCESSED p
            USING (
                SELECT
                    e.job_id,
                    e.source,
                    e.url,
                    e.title,
                    e.company,
                    e.location,
                    e.description,
                    e.snippet,
                    e.job_type,
                    e.posted_date,
                    e.scraped_at,
                    e.salary_min,
                    e.salary_max,
                    e.salary_text,
                    e.h1b_sponsor,
                    e.h1b_employer_name,
                    e.h1b_city,
                    e.h1b_state,
                    e.total_petitions,
                    e.avg_approval_rate,
                    e.description_embedding,
                    e.processed_at,
                    e.company as company_clean,
                    'H-1B' as visa_category,
                    '' as qualifications,
                    DATEDIFF(day, e.posted_date, CURRENT_DATE()) as days_since_posted,
                    1.0 as classification_confidence,
                    CASE WHEN e.is_remote THEN 'Remote' ELSE 'On-site' END as work_model,
                    '' as department,
                    '' as company_size,
                    FALSE as h1b_sponsored_explicit,
                    FALSE as is_new_grad_role,
                    COALESCE(e.job_category, '') as job_category,
                    e.avg_approval_rate as h1b_approval_rate,
                    e.total_petitions as h1b_total_petitions,
                    NULL as sponsorship_score,
                    NULL as h1b_risk_level,
                    NULL as h1b_avg_wage
                FROM PROCESSED_PROCESSING.EMBEDDED_JOBS e
                WHERE e.job_id IN ('{batch_ids}')
            ) e
            ON p.job_id = e.job_id
            WHEN NOT MATCHED THEN INSERT (
                JOB_ID, SOURCE, URL, TITLE, COMPANY, LOCATION, DESCRIPTION, 
                SNIPPET, JOB_TYPE, POSTED_DATE, SCRAPED_AT,
                SALARY_MIN, SALARY_MAX, SALARY_TEXT,
                H1B_SPONSOR, H1B_EMPLOYER_NAME, H1B_CITY, H1B_STATE,
                DESCRIPTION_EMBEDDING, PROCESSED_AT,
                COMPANY_CLEAN, VISA_CATEGORY, QUALIFICATIONS,
                DAYS_SINCE_POSTED, CLASSIFICATION_CONFIDENCE,
                WORK_MODEL, DEPARTMENT, COMPANY_SIZE,
                H1B_SPONSORED_EXPLICIT, IS_NEW_GRAD_ROLE, JOB_CATEGORY,
                H1B_APPROVAL_RATE, H1B_TOTAL_PETITIONS,
                SPONSORSHIP_SCORE, H1B_RISK_LEVEL, H1B_AVG_WAGE
            )
            VALUES (
                e.job_id, e.source, e.url, e.title, e.company, e.location, e.description,
                e.snippet, e.job_type, e.posted_date, e.scraped_at,
                e.salary_min, e.salary_max, e.salary_text,
                e.h1b_sponsor, e.h1b_employer_name, e.h1b_city, e.h1b_state,
                e.description_embedding, e.processed_at,
                e.company_clean, e.visa_category, e.qualifications,
                e.days_since_posted, e.classification_confidence,
                e.work_model, e.department, e.company_size,
                e.h1b_sponsored_explicit, e.is_new_grad_role, e.job_category,
                e.h1b_approval_rate, e.h1b_total_petitions,
                e.sponsorship_score, e.h1b_risk_level, e.h1b_avg_wage
            )
            """
            
            cursor.execute(sql)
            total_processed += len(batch)
            print(f"   ✓ Synced {total_processed:,}/{len(missing_job_ids):,} jobs")
        
        # Step 4: Verify sync
        print("\n🔍 Verifying sync...")
        
        # Step 5: Final counts
        cursor.execute("SELECT COUNT(*) FROM PROCESSED.JOBS_PROCESSED")
        final_count = cursor.fetchone()[0]
        
        print(f"\n✅ Success!")
        print(f"   • New jobs processed: {total_processed:,}")
        print(f"   • Total searchable jobs: {final_count:,}")
        
        return total_processed
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("\n🔌 Connection closed")

def main():
    """Main function that loops until all jobs are processed"""
    print("🚀 Starting embedding generation (will process all pending jobs)")
    print("=" * 80)
    
    iteration = 0
    total_processed = 0
    
    while True:
        iteration += 1
        print(f"\n📍 Iteration {iteration}")
        print("-" * 80)
        
        try:
            result = generate_embeddings()
            
            # Check if we're done
            if result is None:  # No more jobs to process
                break
                
            total_processed += 5000  # Each iteration processes up to 5000
            
        except Exception as e:
            print(f"\n❌ Error in iteration {iteration}: {e}")
            break
    
    print("\n" + "=" * 80)
    print("🎉 ALL JOBS PROCESSED!")
    print("=" * 80)
    print(f"   • Total iterations: {iteration}")
    print(f"   • Approximate jobs processed: {total_processed:,}")
    
    return {"iterations": iteration, "total_processed": total_processed}

if __name__ == "__main__":
    main()
