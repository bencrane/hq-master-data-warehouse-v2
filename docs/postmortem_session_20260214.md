# Session Postmortem - 2026-02-14

## Summary
This session was disorganized and inefficient. Multiple issues arose from poor planning and rushed execution.

## What Was Attempted
1. Attio job postings sync - poorly written Modal function that timed out
2. Person discovery data validation - checked updated_at trigger
3. LinkedIn URL normalization - added computed column
4. Person data export for Attio - SQL query with location cleanup
5. Attio People object setup - added custom attributes
6. Company canonical table - created new table and endpoints
7. Companyenrich data - checked extraction pipeline
8. Attio duplicate company deletion - failed/hung operation

## Issues

### 1. Attio Job Postings Sync Function
- Initial function was poorly architected
- Only fetched 500 companies from Attio (hardcoded limit)
- No pagination for Attio companies
- One-by-one API calls instead of batching
- User correctly identified it as "absolutely awful"
- Resolution: User opted to export CSV manually instead

### 2. Database Queries Timing Out
- Supabase dashboard SQL editor has short timeouts
- Should have used direct psql connection earlier
- Multiple queries failed before switching approaches

### 3. LinkedIn URL Normalization
- Discovered no normalization was happening in extraction code
- Added computed column `linkedin_url_normalized` as safe approach
- Avoided modifying existing data per user's preference

### 4. Companyenrich Extraction Not Updating
- 148 records sent, raw payloads arrived but extracted didn't update
- Root cause: `updated_at` trigger missing on table
- Also: upsert doesn't trigger update if data is identical
- Added trigger, but this should have been caught earlier

### 5. Attio Duplicate Deletion - FAILED
- User accidentally added ~4200 duplicate companies to Attio
- Wrote script to identify and delete duplicates
- Script hung/failed silently with no output
- Background task produced empty output file
- Should have:
  - Tested with small batch first
  - Added better progress logging
  - Considered Attio UI bulk delete as primary option

## Database Changes Made
1. `core.company_canonical` table created
2. `linkedin_url_normalized` computed column added to `extracted.person_discovery`
3. `updated_at` trigger added to `extracted.companyenrich_company`
4. `updated_at` trigger added to `core.company_canonical`

## Endpoints Created
1. `ingest_company_canonical` - upsert cleaned company name + linkedin URL
2. `lookup_company_canonical` - retrieve by domain

## Endpoints NOT Completed
1. `sync_job_postings_to_attio` - exists but poorly written, user abandoned

## Lessons
1. Test complex operations with small batches first
2. Verify database triggers exist before assuming upserts work
3. Use direct database connections for long-running queries
4. Don't attempt bulk API operations without proper error handling and logging
5. When user says code is "absolutely awful" - stop and rewrite properly
6. Background tasks need visible progress indicators

## Cleanup Needed
1. ~3685 duplicate companies still exist in Attio (deletion failed)
2. `sync_job_postings_to_attio` function needs complete rewrite or deletion
3. Consider adding `updated_at` triggers to all extracted tables proactively
