# FIX-001: Person Extraction Column Name Mismatch

**Date:** 2026-01-07  
**Author:** Agent  
**Status:** 🔧 Pending deploy

---

## Summary

Column name mismatch in `extraction/person.py` caused all person profile, experience, and education extraction to fail. Raw payloads were being stored successfully, but extraction threw database errors due to referencing non-existent columns.

---

## Symptom

- Records sent to `ingest-clay-person-profile` endpoint
- `raw.person_payloads` received the data ✅
- `extracted.person_profile` was empty ❌
- `extracted.person_experience` was empty ❌
- `extracted.person_education` was empty ❌

---

## Root Cause

Two column names in the extraction code did not match the actual database schema:

| Location | Code Used | Actual DB Column |
|----------|-----------|------------------|
| `extraction/person.py` line 61 | `latest_company_linkedin_org_id` | `latest_company_org_id` |
| `extraction/person.py` line 141 | `company_linkedin_org_id` | `company_org_id` |

When Supabase tried to insert with these non-existent column names, it threw an error. The error was caught by the try/except in `ingest/person.py` (lines 104-105) but by that point, the raw insert had already succeeded (line 66-78 runs before extraction on lines 82-94).

---

## Fix

**File:** `modal-mcp-server/src/extraction/person.py`

### Change 1: Line 61

```python
# Before
"latest_company_linkedin_org_id": latest_exp.get("org_id"),

# After
"latest_company_org_id": latest_exp.get("org_id"),
```

### Change 2: Line 141

```python
# Before
"company_linkedin_org_id": exp.get("org_id"),

# After
"company_org_id": exp.get("org_id"),
```

---

## Verification

After deploying, send a test record to `ingest-clay-person-profile` and verify:

1. `raw.person_payloads` has the record
2. `extracted.person_profile` has the record
3. `extracted.person_experience` has rows (if experience array was non-empty)
4. `extracted.person_education` has rows (if education array was non-empty)

SQL to verify Douglas Hanna record (the first test case):

```sql
SELECT id, full_name, latest_title, latest_company 
FROM extracted.person_profile 
WHERE linkedin_url = 'https://www.linkedin.com/in/douglashanna1';

SELECT COUNT(*) as experience_count 
FROM extracted.person_experience 
WHERE linkedin_url = 'https://www.linkedin.com/in/douglashanna1';

SELECT COUNT(*) as education_count 
FROM extracted.person_education 
WHERE linkedin_url = 'https://www.linkedin.com/in/douglashanna1';
```

---

## Backfill Required

Raw payloads exist in `raw.person_payloads` that were never extracted. After fix is deployed, these should be re-processed:

```sql
-- Count records needing backfill
SELECT COUNT(*) 
FROM raw.person_payloads rp
LEFT JOIN extracted.person_profile ep ON ep.raw_payload_id = rp.id
WHERE ep.id IS NULL;
```

---

## Deployment

```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server/src
git checkout main
git pull origin main
git status  # Must be clean
modal deploy app.py
```

