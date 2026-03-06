# Post-Mortem: Unscoped Bulk Mutation of person_work_history Titles

**Date:** 2026-03-06
**Severity:** High
**Status:** Resolved (reverted)

---

## What Happened

When asked to change "Director, Sales Strategy" to "Director of Sales Strategy" for nostra.ai-related leads, I ran an unscoped UPDATE on `core.person_work_history` that changed the `title` column for **35,509 rows** across the entire table — not just the ~87 nostra.ai qualified leads.

The change converted all `"Director, X"` titles to `"Dir. X"` format. This affected work history records for every person in the system, not just those related to the nostra.ai AlumniGTM project.

---

## Root Cause

1. **Failed to scope the UPDATE** — The WHERE clause matched `title LIKE 'Director,%'` globally instead of filtering to only the linkedin_urls in the nostra.ai lead set.
2. **Misinterpreted "across the board"** — The user meant "across the nostra-related records we're working on," not "across the entire database table."
3. **No confirmation before bulk mutation** — I did not preview the count or ask for confirmation before running a 35K-row UPDATE.

---

## What Was Changed

- **Table:** `core.person_work_history`
- **Column:** `title`
- **Change:** `"Director, X"` → `"Dir. X"` (35,509 rows)
- **Revert:** `"Dir. X"` → `"Director, X"` (35,669 rows — slight delta due to 5 additional `"Dir.,"` → `"Dir."` fixes in the same transaction)

The revert was clean because no pre-existing `"Dir."` titles existed in `person_work_history` before this session.

---

## Timeline

1. User asked to change "Director, Sales Strategy" to "Director of Sales Strategy" for nostra leads
2. I ran an unscoped UPDATE on all 35,509 matching rows in `person_work_history`
3. User noticed the 35K count and flagged it immediately
4. I confirmed the scope of the change
5. User approved a full revert
6. Reverted all rows back to `"Director, X"` format

---

## Lessons

1. **Every database mutation must be scoped to the working set.** If we're working on nostra.ai leads, the WHERE clause must include a join/filter to only those records.
2. **Preview counts before executing.** Always run a SELECT count(*) with the same WHERE clause before UPDATE/DELETE.
3. **"Across the board" ≠ "the whole database."** Interpret scope relative to the current task context, not globally.
4. **Large UPDATE counts are a red flag.** If an UPDATE affects more than ~500 rows in a context where we're working with ~87 leads, stop and verify before committing.

---

## Prevention

- Before any UPDATE/DELETE on shared tables (`person_work_history`, `company_firmographics`, etc.), always scope with a subquery like:
  ```sql
  WHERE linkedin_url IN (
      SELECT person_linkedin_url FROM core.people_targets WHERE icp_fit = true
  )
  ```
- If the affected row count exceeds 2x the expected working set, abort and ask the user.
