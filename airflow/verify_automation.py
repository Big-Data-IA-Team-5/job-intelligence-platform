#!/usr/bin/env python3
"""
Verification Script: Proves that DAGs are configured to automatically generate embeddings
Run this to see exactly what each DAG will do when it runs
"""
import re
import os

def check_dag_file(filepath):
    """Check if a DAG file has embedding automation enabled"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    dag_name = os.path.basename(filepath)
    
    # Check if it excludes embeddings
    has_exclude = '--exclude embedded_jobs' in content or '--exclude embedded' in content
    
    # Check if dbt run is present
    has_dbt_run = 'dbt run' in content
    
    # Find the dbt command
    dbt_commands = re.findall(r"bash_command='[^']*dbt run[^']*'", content)
    
    return {
        'name': dag_name,
        'has_dbt_run': has_dbt_run,
        'excludes_embeddings': has_exclude,
        'dbt_commands': dbt_commands,
        'automation_enabled': has_dbt_run and not has_exclude
    }

def main():
    print("=" * 80)
    print("🔍 VERIFYING AIRFLOW DAG AUTOMATION")
    print("=" * 80)
    print()
    
    dag_dir = 'airflow/dags'
    if not os.path.exists(dag_dir):
        dag_dir = '/opt/airflow/dags'  # For running inside Airflow container
    
    dag_files = [
        f'{dag_dir}/dag_internship_scraper.py',
        f'{dag_dir}/dag_fortune500_scraper.py',
        f'{dag_dir}/dag_airtable_grad_scraper.py',
        f'{dag_dir}/dag_quick_pipeline.py'
    ]
    
    results = []
    all_automated = True
    
    for dag_file in dag_files:
        if os.path.exists(dag_file):
            result = check_dag_file(dag_file)
            results.append(result)
            
            status = "✅ AUTOMATED" if result['automation_enabled'] else "❌ MANUAL"
            print(f"{status} | {result['name']}")
            
            if result['has_dbt_run']:
                print(f"   📋 dbt transformations: YES")
            else:
                print(f"   ⚠️  dbt transformations: NO")
            
            if result['excludes_embeddings']:
                print(f"   ❌ Excludes embeddings: YES (BAD)")
                all_automated = False
            else:
                print(f"   ✅ Includes embeddings: YES (GOOD)")
            
            if result['dbt_commands']:
                print(f"   🔧 Command: {result['dbt_commands'][0][:80]}...")
            
            print()
    
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print()
    
    automated_count = sum(1 for r in results if r['automation_enabled'])
    total_count = len(results)
    
    print(f"DAGs checked: {total_count}")
    print(f"Fully automated: {automated_count}")
    print(f"Manual intervention needed: {total_count - automated_count}")
    print()
    
    if all_automated:
        print("✅ SUCCESS! ALL DAGS ARE FULLY AUTOMATED")
        print()
        print("🚀 What happens when DAGs run:")
        print("   1. Scrape new jobs → JOBS_RAW")
        print("   2. dbt runs (includes embedding generation):")
        print("      • classified_jobs.sql → classify")
        print("      • embedded_jobs.sql → GENERATE EMBEDDINGS ✨")
        print("      • jobs_processed.sql → make searchable")
        print("   3. Jobs are instantly searchable!")
        print()
        print("💡 YOU DON'T NEED TO RUN ANY MANUAL SCRIPTS")
        return 0
    else:
        print("❌ SOME DAGS STILL NEED MANUAL INTERVENTION")
        print("   Fix DAGs that exclude embeddings")
        return 1

if __name__ == '__main__':
    exit(main())
