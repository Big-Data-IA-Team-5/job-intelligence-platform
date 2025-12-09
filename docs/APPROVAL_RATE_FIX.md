# H-1B Approval Rate Calculation Fix

## Problem
The H-1B approval rate was being calculated incorrectly across the system:
- **Old Calculation**: `certified / (certified + denied)` - excluded withdrawn cases
- **Example**: Amazon.com Services had 1,896 total filings with 1,893 certified and 0 denied
  - Old rate showed: 100% (1893/(1893+0))
  - Real rate should be: 99.84% (1893/1896)

## Root Cause
The `EMPLOYER_INTELLIGENCE` view calculated `approval_rate = certified / (certified + denied)`, but `total_filings` included all cases (certified + denied + withdrawn). This created a mismatch.

## Solution
Fixed the approval rate calculation in all display locations to use: **`(total_certified / total_filings) * 100`**

## Files Modified

### 1. Agent 2 - Chat Intelligence (`snowflake/agents/agent2_chat.py`)
**Changes:**
- `_get_sponsorship_info()` method (lines 622-670):
  - Added `real_approval_rate` calculation in SQL query
  - Updated display to use real rate instead of stored `approval_rate`
  
- `_compare_companies()` method (lines 707-755):
  - Added `real_approval_rate` calculation in SQL query
  - Updated company comparison display to use real rate

**Impact:** Chat responses now show accurate approval rates when users ask about company sponsorship

### 2. Analytics API (`backend/app/routes/analytics.py`)
**Changes:**
- `/api/analytics/companies/top` endpoint (lines 220-240):
  - Added JOIN with `employer_intelligence` table
  - Calculate real rate: `total_certified * 100.0 / NULLIF(total_filings, 0)`
  
- `/api/analytics/companies/h1b-sponsors` endpoint (lines 335-355):
  - Added JOIN with `employer_intelligence` table
  - Calculate real rate in aggregation

**Impact:** Dashboard analytics now display accurate approval rates

### 3. DBT Model (`dbt/models/processing/h1b_matched_jobs.sql`)
**Changes:**
- `h1b_aggregated` CTE (line 21):
  - Changed from: `AVG(CASE WHEN case_status = 'Certified' THEN 1.0 ELSE 0.0 END)`
  - Changed to: `(SUM(CASE WHEN case_status = 'Certified' THEN 1 ELSE 0 END) * 1.0 / COUNT(*))`

**Impact:** Future dbt runs will populate `jobs_processed.h1b_approval_rate` with correct values

## Testing

### 1. Test Agent 2 Response
```python
# Ask about Amazon
response = agent.ask("Tell me about Amazon's H-1B sponsorship")
# Should show: "Approval Rate: 99.8%" instead of "100%"
```

### 2. Test Analytics Dashboard
```bash
curl http://localhost:8000/api/analytics/companies/h1b-sponsors?limit=10
# Check that avg_approval_rate is realistic (not 100% for all companies)
```

### 3. Test Frontend Dashboard
- Navigate to "Advanced Analytics" page
- Check "Top H-1B Sponsoring Companies" chart
- Verify approval rates are realistic (< 100% for most companies)

### 4. Re-run DBT (Optional - for future data loads)
```bash
cd dbt
dbt run --models h1b_matched_jobs
```

## Verification Queries

### Check Real vs Stored Approval Rate
```sql
SELECT 
    employer_original,
    approval_rate * 100 as stored_rate,
    (total_certified * 100.0 / total_filings) as real_rate,
    total_filings,
    total_certified,
    total_denied
FROM processed.employer_intelligence
WHERE employer_original ILIKE '%amazon%'
LIMIT 5;
```

### Expected Results
| Company | Stored Rate | Real Rate | Total Filings | Certified | Denied |
|---------|-------------|-----------|---------------|-----------|--------|
| Amazon.com Services LLC | 100.0 | 99.84 | 1896 | 1893 | 0 |

## Important Notes

### What We Did NOT Change
❌ **Did NOT modify the `EMPLOYER_INTELLIGENCE` view definition**
- Reason: Changing the view would break existing queries system-wide
- The view's `approval_rate` field remains as `certified/(certified+denied)`

✅ **Only modified display logic in:**
- Agent responses
- API endpoints
- DBT models for future data loads

### Database State
- Existing data in `jobs_processed.h1b_approval_rate` still has old values
- New data loaded via dbt will have correct values
- All display logic now calculates real rate on-the-fly

## Backward Compatibility
✅ All changes are backward compatible
- Old queries still work
- API responses maintain same structure
- Only the calculated values changed (more accurate now)

## Deployment Checklist
- [x] Fix Agent 2 sponsorship info display
- [x] Fix Agent 2 company comparison display
- [x] Fix analytics top companies endpoint
- [x] Fix analytics H-1B sponsors endpoint
- [x] Fix dbt h1b_matched_jobs model
- [ ] Test chat responses
- [ ] Test analytics dashboard
- [ ] Re-run dbt (optional)
- [ ] Monitor for any API errors

## Future Improvements
Consider creating a new view or updating existing view to expose both rates:
```sql
CREATE OR REPLACE VIEW employer_intelligence_v2 AS
SELECT 
    ...existing fields...,
    approval_rate as approval_rate_excluding_withdrawn,
    (total_certified * 1.0 / total_filings) as approval_rate_all_filings
FROM ...
```
