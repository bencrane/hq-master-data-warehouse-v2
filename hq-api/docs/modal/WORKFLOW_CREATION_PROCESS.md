# Modal Workflow Creation Process

Standard process for creating new Modal ingest workflows. **Always complete documentation before moving to the next workflow.**

---

## The Flow

```
1. Design → 2. Build → 3. Test → 4. Iterate → 5. Document → 6. Next
```

**Rule:** Do NOT move to the next workflow until documentation is complete and committed.

---

## Step 1: Design

1. **Get sample payload** from the provider (Clay enrichment column, API response, etc.)
2. **Define the request schema** - what fields will you send from Clay?
   - Canonical fields (your source of truth): `first_name`, `last_name`, `domain`, etc.
   - Raw payload field: `<provider>_raw_payload`
3. **Decide on table structure:**
   - `raw.<entity>_<provider>` - stores incoming payloads
   - `extracted.<entity>_<provider>` - flattened/normalized data
   - Any reference tables needed?

---

## Step 2: Build

1. **Create migration** in `supabase/migrations/`
   - Raw table
   - Extracted table
   - Reference tables (if any)
   - Indexes
   - Workflow registry entry

2. **Apply migration** via psql:
   ```bash
   psql "postgresql://..." -f supabase/migrations/<migration>.sql
   ```

3. **Create extraction function** in `src/extraction/<name>.py`

4. **Create ingest function** in `src/ingest/<name>.py`
   - Pydantic request model
   - `@app.function()` and `@modal.fastapi_endpoint()` decorators
   - Lazy imports inside function body

5. **Update `src/app.py`**
   - Add import for ingest function
   - Add import for extraction module
   - Add to `__all__` list

6. **Deploy:**
   ```bash
   cd modal-mcp-server
   uv run modal deploy src/app.py
   ```

---

## Step 3: Test

1. **Send test records** from Clay (small batch, 5-10 records)
2. **Check tables** via psql:
   ```sql
   SELECT * FROM extracted.<table> ORDER BY created_at DESC LIMIT 10;
   ```
3. **Verify data looks correct:**
   - Fields populated as expected?
   - Reference tables updated?
   - No errors in response?

---

## Step 4: Iterate

Common issues and fixes:

| Issue | Fix |
|-------|-----|
| Field not populated | Check Clay webhook mapping |
| Wrong field name | Update Pydantic model, redeploy |
| Column doesn't exist | Add via `ALTER TABLE`, update migration |
| Reference table not updating | Check conditional logic in extraction |
| Literal string instead of value | Fix Clay mapping (use column reference, not string) |

**After each fix:**
1. Redeploy: `uv run modal deploy src/app.py`
2. Delete test records: `DELETE FROM extracted.<table>; DELETE FROM raw.<table>;`
3. Resend test batch
4. Verify

---

## Step 5: Document

**Before moving on, create/update documentation:**

1. **Create workflow doc** at `docs/modal/workflows/<workflow-name>.md`:
   - Endpoint URL
   - Request payload structure
   - Field descriptions
   - Response format
   - Database tables (raw, extracted, reference)
   - File locations

2. **Update migration file** to reflect final state (if changes were made during iteration)

3. **Template:** Copy from an existing workflow doc (e.g., `signal-job-change.md` or `email-anymailfinder.md`)

---

## Step 6: Next Workflow

Only after documentation is complete:
1. Commit all changes
2. Start next workflow from Step 1

---

## File Checklist

For each new workflow, you should have:

- [ ] `supabase/migrations/<date>_<name>.sql` - Migration file
- [ ] `src/ingest/<name>.py` - Ingest function
- [ ] `src/extraction/<name>.py` - Extraction function
- [ ] `src/app.py` - Updated with imports
- [ ] `docs/modal/workflows/<name>.md` - Documentation

---

## Quick Reference

**Deploy:**
```bash
cd /Users/benjamincrane/hq-master-data-warehouse-v2/modal-mcp-server
uv run modal deploy src/app.py
```

**Check tables:**
```bash
psql "postgresql://postgres:rVcat1Two1d8LQVE@db.ivcemmeywnlhykbuafwv.supabase.co:5432/postgres"
```

**Delete test data:**
```sql
DELETE FROM extracted.<table>;
DELETE FROM raw.<table>;
DELETE FROM reference.<table>;  -- if applicable
```

**Get counts:**
```sql
SELECT COUNT(*) FROM extracted.<table>;
SELECT COUNT(*) FROM reference.<table>;
```
