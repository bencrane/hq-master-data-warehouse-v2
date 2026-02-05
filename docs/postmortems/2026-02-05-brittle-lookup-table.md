# Post-Mortem: Brittle Lookup Table — Ignored Existing Codebase Patterns

**Date:** 2026-02-05
**Severity:** Medium
**Status:** Resolved

---

## What Happened

Asked to create `reference.company_type_lookup` to map raw company type values (from companyenrich and company_discovery) to canonical types. Instead of studying how the codebase already handles this exact problem for other dimensions, I invented my own approach. The result was a fragile, inconsistent table that didn't match anything else in the project.

### What I Built (Wrong)

```sql
CREATE TABLE reference.company_type_lookup (
    raw_type TEXT PRIMARY KEY,
    canonical_type TEXT NOT NULL REFERENCES reference.company_types(name)
);
```

- **21 rows** — stored both cased and lowercased versions of every raw value as separate rows (e.g., `"Privately Held"` AND `"privately held"` as two separate entries)
- Column names `raw_type` and `canonical_type` — made-up names that don't match any other lookup table in the schema
- Did not update the ingest code to use the table — left the hardcoded Python dict in place, making the table dead on arrival

### What It Should Have Been (Correct)

```sql
CREATE TABLE reference.company_type_lookup (
    raw_value TEXT PRIMARY KEY,
    matched_company_type TEXT NOT NULL REFERENCES reference.company_types(name)
);
```

- **13 rows** — all lowercase, because the ingest code calls `.lower()` before lookup (same as every other ingest function)
- Column names `raw_value` and `matched_company_type` — matching the established pattern (`employee_range_lookup.raw_value → size_cleaned`, `revenue_range_lookup.raw_value → matched_revenue_range`, `funding_range_lookup.raw_value → matched_funding_range`)
- Ingest code updated to query the table instead of using a hardcoded dict — making the table actually do something

---

## Root Cause

**Did not read existing code before writing new code.**

The project has at least four lookup tables that solve the exact same problem for other dimensions:

| Table | Raw Column | Canonical Column | Pattern |
|-------|-----------|-----------------|---------|
| `reference.employee_range_lookup` | `size_raw` | `size_cleaned` | `.eq("size_raw", raw_value)` |
| `reference.revenue_range_lookup` | `raw_value` | `matched_revenue_range` | `.eq("raw_value", raw_value)` |
| `reference.funding_range_lookup` | `raw_value` | `matched_funding_range` | `.eq("raw_value", raw_value)` |
| `reference.industry_lookup` | `industry_raw` | `industry_cleaned` | `.ilike("industry_cleaned", value)` |

All of these:
1. Store raw values **once**, in the form the ingest code will query (lowercase)
2. Use `raw_value` as the PK column name (or similar)
3. Use `matched_*` as the canonical column name
4. Are actually queried by ingest code via `supabase.schema("reference").from_("...").select("...").eq("raw_value", value.lower())`

I checked none of them. I just created a table from scratch with made-up column names and a redundant row strategy.

### Why Storing Both Cases Is Brittle

If a new source sends `"PRIVATE"` or `"Private"` or `"PRIVATELY HELD"`, the table would need yet another row for each casing variant. The correct approach — store lowercase, call `.lower()` at query time — handles all casing for free. This is already what every other ingest function does. Duplicating cased rows means:
- Every new source or casing variant requires a new row
- No single source of truth — the "same" mapping exists in multiple rows
- Table grows linearly with the number of casing variants, not the number of distinct raw values

### Why Not Updating Ingest Code Made It Useless

The table was created but the Python code still used `COMPANY_TYPE_MAP = {...}` — a hardcoded dict. The table would never be queried. It existed only in the database with no consumer. This defeats the entire purpose: the point of a reference table is that the ingest code looks up values from it, so adding new mappings is a database operation, not a code deploy.

---

## What Should Have Been Done

1. **Before writing any SQL, read the existing lookup tables.** Run `\d reference.employee_range_lookup`, `\d reference.revenue_range_lookup`, `\d reference.funding_range_lookup`. See the column naming pattern. See how the ingest code queries them.

2. **Before writing any SQL, read the ingest code that will consume the table.** Look at how `companyenrich.py` already uses `employee_range_lookup` (lines 128-136) and `revenue_range_lookup` (lines 152-159). Copy that exact pattern.

3. **Match the established naming convention.** `raw_value` for the PK. `matched_{dimension}` for the canonical FK.

4. **Store values once, lowercase.** The ingest code normalizes with `.lower()`. The table doesn't need to handle casing.

5. **Update the ingest code in the same change.** A lookup table without a consumer is dead code.

---

## Fixes Applied

1. Dropped the bad table and recreated with correct schema (`raw_value`, `matched_company_type`)
2. 13 rows, all lowercase
3. Updated `companyenrich.py` to query `reference.company_type_lookup` instead of using `COMPANY_TYPE_MAP` dict
4. Updated `companyenrich_similar_companies_preview_results.py` — same change, removed its own stale `COMPANY_TYPE_MAP` (which was even worse: only 3 entries, and one mapped to the old canonical name `Self-Employed` instead of `Sole Proprietorship`)
5. Deployed to Modal

---

## Lesson

When a codebase already solves a problem N times, the N+1th solution should look identical. Don't invent. Read the existing implementations first, then copy the pattern. The 10 minutes spent reading `employee_range_lookup` and its consumer code would have produced the correct table on the first try.

---

## Rule Added

**Before creating any new reference/lookup table:** Read at least two existing lookup tables (`\d reference.*_lookup`) and their corresponding ingest code queries. Match the column naming, row strategy, and query pattern exactly.
