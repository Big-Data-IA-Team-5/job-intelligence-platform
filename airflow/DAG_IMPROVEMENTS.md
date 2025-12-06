# DAG Pipeline Improvements

## ✅ What Changed

All production DAGs have been **standardized to follow the test pipeline structure** with proper task dependencies and unified JSON storage.

## 🔄 Updated DAGs

### 1. **airtable_grad_scraper** (Graduate Jobs)
- **Schedule**: Daily at 2 AM UTC (`0 2 * * *`)
- **Pipeline Flow**: Scrape → S3 Upload → Snowflake Upload → Summary
- **Output**: `raw/airtable/grad/grad_jobs_{timestamp}.json`
- **Tags**: `scraper`, `airtable`, `new-grad`, `jobs`, `pipeline`

### 2. **internship_scraper** (Internship Jobs)
- **Schedule**: Daily at 2 AM UTC (`0 2 * * *`)
- **Pipeline Flow**: Scrape → S3 Upload → Snowflake Upload → Summary
- **Output**: `raw/airtable/internships/internship_jobs_{timestamp}.json`
- **Tags**: `scraper`, `airtable`, `internships`, `intern-list`, `pipeline`

### 3. **fortune500_scraper** (Fortune 500 Companies)
- **Schedule**: Weekly on Mondays at 1 AM UTC (`0 1 * * 1`)
- **Pipeline Flow**: Scrape → S3 Upload → Snowflake Upload → Summary
- **Output**: `raw/fortune500/fortune500_jobs_{timestamp}.json`
- **Tags**: `scraper`, `fortune500`, `companies`, `weekly`, `pipeline`

### 4. **h1b_loader** (H-1B Data)
- **Schedule**: Manual trigger only (quarterly data updates)
- **Pipeline Flow**: Load → S3 Upload → Snowflake Upload → Summary
- **Output**: `raw/h1b/h1b_data_{timestamp}.json`
- **Tags**: `loader`, `h1b`, `data`, `manual`, `pipeline`

## 🎯 Key Improvements

### 1. **Unified Pipeline Structure**
All DAGs now follow the same 4-task pattern:
```
Task 1: Data Collection (Scrape/Load)
   ↓
Task 2: S3 Upload (Raw JSON with timestamp)
   ↓
Task 3: Snowflake Upload (Database storage)
   ↓
Task 4: Summary Report (Pipeline metrics)
```

### 2. **Consistent JSON Storage**
- All scrapers store data in **timestamped JSON files**
- Path structure: `raw/{source_type}/{job_type}_{timestamp}.json`
- No file overwrites - append-only approach
- 30-day retention (90 days for H-1B)

### 3. **Proper Task Dependencies**
- Tasks execute sequentially with clear dependencies
- XCom used for data passing between tasks
- Proper error handling and rollback

### 4. **Enhanced Logging**
Each task provides clear step-by-step output:
```
===============================================================================
STEP 1: SCRAPING GRADUATE JOBS FROM AIRTABLE
===============================================================================

⚙️  Configuration:
   Time window: Last 720 hours (30.0 days)
   Workers: 5

🚀 Starting scraper...
```

### 5. **Pipeline Summary**
Each DAG run ends with a comprehensive summary:
```
===============================================================================
🎯 GRADUATE JOBS PIPELINE SUMMARY
===============================================================================

📊 Results:
   ✓ Jobs scraped: 1,234
   ✓ S3 path: s3://bucket/raw/airtable/grad/grad_jobs_20251205_020045.json
   ✓ Snowflake table: job_intelligence.raw.jobs_raw

✅ PIPELINE COMPLETED SUCCESSFULLY!
===============================================================================
```

## 📁 Storage Structure

### S3 Bucket Organization
```
s3://job-intelligence-bucket/
├── raw/
│   ├── airtable/
│   │   ├── grad/
│   │   │   ├── grad_jobs_20251205_020045.json
│   │   │   └── grad_jobs_20251206_020112.json
│   │   └── internships/
│   │       ├── internship_jobs_20251205_020234.json
│   │       └── internship_jobs_20251206_020301.json
│   ├── fortune500/
│   │   ├── fortune500_jobs_20251202_010512.json
│   │   └── fortune500_jobs_20251209_010645.json
│   └── h1b/
│       └── h1b_data_20251201_143022.json
```

### Snowflake Tables
```sql
-- All job postings (Fortune 500, Grad, Internships)
job_intelligence.raw.jobs_raw

-- H-1B disclosure data
job_intelligence.raw.h1b_raw
```

## 🔧 Benefits

1. **Consistency**: All DAGs follow the same pattern
2. **Traceability**: Timestamped files provide historical tracking
3. **Reliability**: Proper task dependencies prevent data corruption
4. **Maintainability**: Easy to add new scrapers following this template
5. **Monitoring**: Clear summaries make it easy to track pipeline health
6. **Data Quality**: Automatic cleanup of old S3 files prevents storage bloat

## 🚀 Next Steps

To activate all DAGs:
1. Access Airflow UI at `http://localhost:8080`
2. Enable each DAG by toggling the switch
3. Monitor the first run of each DAG
4. Verify data appears in S3 and Snowflake

## 📊 Expected Schedule

| DAG | Frequency | Day | Time (UTC) | Duration |
|-----|-----------|-----|------------|----------|
| Graduate Jobs | Daily | Every day | 02:00 | ~30 min |
| Internships | Daily | Every day | 02:00 | ~30 min |
| Fortune 500 | Weekly | Monday | 01:00 | ~4-6 hrs |
| H-1B Loader | Manual | On-demand | N/A | ~15 min |

## 🔍 Monitoring Tips

1. **Check DAG Success Rate**: Airflow UI → DAGs → Success/Failure metrics
2. **Verify S3 Uploads**: Check S3 bucket for new timestamped files
3. **Validate Snowflake Data**: Query tables to verify row counts
4. **Review Logs**: Check task logs for any warnings or errors
5. **Monitor Duration**: Track execution time to identify performance issues

---

**Status**: ✅ All 4 production DAGs updated and ready for deployment
**Date**: December 5, 2025
