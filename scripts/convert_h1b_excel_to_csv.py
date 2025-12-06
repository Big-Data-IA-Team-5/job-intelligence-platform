#!/usr/bin/env python3
"""
One-time script to convert H-1B Excel file to CSV for fast loading.
This avoids the 30-50 minute Excel parsing time in Airflow DAGs.

Usage:
    python scripts/convert_h1b_excel_to_csv.py
"""

import pandas as pd
from pathlib import Path
import sys

def convert_excel_to_csv():
    """Convert H-1B Excel file to CSV for fast loading"""
    
    # Define paths
    project_root = Path(__file__).parent.parent
    excel_path = project_root / "data" / "LCA_Disclosure_Data_FY2025_Q3.xlsx"
    csv_path = project_root / "data" / "LCA_Disclosure_Data_FY2025_Q3.csv"
    
    # Check if Excel file exists
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        print(f"   Please download it first")
        sys.exit(1)
    
    # Check if CSV already exists
    if csv_path.exists():
        print(f"⚠️  CSV already exists: {csv_path}")
        response = input("   Overwrite? (yes/no): ").strip().lower()
        if response != 'yes':
            print("   Cancelled")
            sys.exit(0)
    
    print(f"🔄 Converting Excel to CSV...")
    print(f"   Source: {excel_path}")
    print(f"   Target: {csv_path}")
    print(f"   This will take 30-50 minutes (one-time operation)...")
    print()
    
    try:
        # Read Excel (slow)
        print("📖 Reading Excel file...")
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        print(f"✅ Loaded {len(df):,} rows")
        print(f"   Columns: {list(df.columns)}")
        print()
        
        # Write CSV (fast)
        print("💾 Writing CSV file...")
        df.to_csv(csv_path, index=False)
        
        # Verify
        csv_size_mb = csv_path.stat().st_size / 1024 / 1024
        excel_size_mb = excel_path.stat().st_size / 1024 / 1024
        
        print()
        print("=" * 80)
        print("✅ CONVERSION COMPLETE!")
        print("=" * 80)
        print(f"📊 Excel file: {excel_size_mb:.1f} MB")
        print(f"📊 CSV file:   {csv_size_mb:.1f} MB")
        print(f"📊 Rows:       {len(df):,}")
        print()
        print("🚀 Future H-1B DAG runs will use CSV and complete in ~30 seconds!")
        print()
        
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    convert_excel_to_csv()
