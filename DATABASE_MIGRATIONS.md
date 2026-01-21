# Database Migrations Guide

## Core Principle

**Migration files are the source of truth for database schema.** Any change made to the database must also be reflected in the corresponding migration file.

## Why This Matters

1. **Reproducibility**: Migration files allow recreating the database from scratch
2. **Version Control**: Git tracks all schema changes over time
3. **Collaboration**: Other developers can see exactly what the schema looks like
4. **Disaster Recovery**: If the database is lost, migrations rebuild it

## Workflow

### Creating New Tables

1. Create a new migration file: `supabase/migrations/YYYYMMDD_descriptive_name.sql`
2. Write all CREATE TABLE, CREATE INDEX, and INSERT statements
3. Run the SQL in Supabase SQL Editor
4. Verify with a SELECT query

### Modifying Existing Tables

1. Run the ALTER TABLE / UPDATE in Supabase SQL Editor
2. **Immediately** update the original migration file to reflect the final schema
3. The migration file should represent the *current* state, not a history of changes

### Example: Adding a Column

```sql
-- Run in Supabase SQL Editor:
ALTER TABLE extracted.case_study_details 
ADD COLUMN IF NOT EXISTS confidence TEXT;
```

Then update the migration file's CREATE TABLE to include the new column:

```sql
-- In migration file (updated):
CREATE TABLE IF NOT EXISTS extracted.case_study_details (
    ...
    confidence TEXT,  -- Added
    ...
);
```

### Example: Changing a Value

```sql
-- Run in Supabase SQL Editor:
UPDATE reference.enrichment_workflow_registry 
SET workflow_slug = 'new-slug'
WHERE workflow_slug = 'old-slug';
```

Then update the migration file's INSERT:

```sql
-- In migration file (updated):
INSERT INTO reference.enrichment_workflow_registry (...) 
VALUES ('new-slug', ...);  -- Changed from 'old-slug'
```

## Migration File Naming

Format: `YYYYMMDD_descriptive_name.sql`

Examples:
- `20260107_company_customer_claygent.sql`
- `20260108_case_study_extraction.sql`

## Current Migration Files

| File | Purpose |
|------|---------|
| `20260107_company_customer_claygent.sql` | Company customer data from Claygent |
| `20260108_case_study_extraction.sql` | Case study details + champions from Gemini |

## Checklist

Before considering a database change complete:

- [ ] SQL ran successfully in Supabase
- [ ] Migration file updated to reflect final schema
- [ ] Migration file committed to git
- [ ] Any dependent code (Modal functions, etc.) updated and deployed

