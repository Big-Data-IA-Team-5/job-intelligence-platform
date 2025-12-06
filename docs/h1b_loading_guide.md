# H-1B Data Loading - Quick Start Guide

## Problem
The H-1B Excel file (258MB) takes **30-50 minutes** to parse with pandas, causing Airflow tasks to timeout.

## Solution
Convert Excel → CSV **once** on your local machine. Future loads take ~30 seconds.

## Steps

### 1. Run Conversion Script (One Time)
```bash
cd /Users/pranavpatel/Desktop/job-intelligence-platform
python scripts/convert_h1b_excel_to_csv.py
```

This will:
- Read `data/LCA_Disclosure_Data_FY2025_Q3.xlsx` (30-50 min)
- Write `data/LCA_Disclosure_Data_FY2025_Q3.csv` (instant)
- Show progress and completion stats

### 2. Rebuild Airflow (to mount the CSV)
```bash
cd airflow
docker-compose down
docker-compose up -d --build
```

### 3. Run H-1B DAG
The DAG will now:
- Detect CSV file
- Load in ~30 seconds
- Upload to Snowflake via batch insert

## Performance Comparison

| Method | Time | Notes |
|--------|------|-------|
| Excel (pandas.read_excel) | 30-50 min | ❌ Gets killed by Airflow timeout |
| CSV (pandas.read_csv) | ~30 sec | ✅ Fast, reliable |

## File Locations

- **Excel source**: `data/LCA_Disclosure_Data_FY2025_Q3.xlsx` (258 MB)
- **CSV output**: `data/LCA_Disclosure_Data_FY2025_Q3.csv` (~150 MB)
- **Conversion script**: `scripts/convert_h1b_excel_to_csv.py`
- **DAG**: `airflow/dags/dag_h1b_loader.py`

## Troubleshooting

### CSV not found in Airflow
Make sure the CSV is in the `data/` directory and rebuild containers:
```bash
ls -lh data/LCA_Disclosure_Data_FY2025_Q3.csv
cd airflow && docker-compose up -d --build
```

### Conversion taking too long
This is normal! Excel parsing is slow. Let it run in the background:
```bash
# Run in background
nohup python scripts/convert_h1b_excel_to_csv.py > /tmp/h1b_convert.log 2>&1 &

# Check progress
tail -f /tmp/h1b_convert.log
```

## Future Updates

When Q4 data is released:
1. Download new Excel file
2. Update filename in script
3. Run conversion once
4. Rebuild Airflow
