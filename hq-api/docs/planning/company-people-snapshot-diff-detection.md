# Company People Snapshot Diff Detection

**Status:** Planning
**Created:** 2026-01-30

## Overview

Detect **senior hires** and **departures** by comparing periodic "find people" snapshots for target companies. Free signal detection (no per-record Clay cost) using Clay's free find-people action.

## The Signal

```
Week 1 Snapshot (Company X)     Week 2 Snapshot (Company X)
├── Person A (VP Sales)         ├── Person A (VP Sales)        → No change
├── Person B (CTO)              ├── Person C (CTO)             → B departed, C hired
├── Person D (Director Eng)                                     → D departed
                                ├── Person E (VP Marketing)     → E hired
```

## Value Proposition

- Free signal detection (no per-signal Clay credits)
- Detect senior exec hires/departures across thousands of companies
- Weekly or regular cadence (Clay scheduled)
- Scalable to 100k+ companies

---

## Architecture

### Key Design Decisions

| Decision | Recommendation |
|----------|----------------|
| Company identifier | `linkedin_company_url` (more stable than domain) |
| Person identifier | `linkedin_url` (unique per person) |
| Snapshot grouping | `snapshot_batch_id` + `snapshot_date` |
| Diff granularity | Per-company, compare consecutive snapshots |
| Processing mode | Batch (triggered by Clay after ingest complete) |
| Title filtering | Query time, not detection time |
| False positives | Not our problem - store what we get |

### Batch ID Strategy

`snapshot_batch_id` generated in Clay: `{company_linkedin_url}_{date}` or similar.

Passed with each record so detection endpoint knows which records belong together.

---

## Proposed Tables

### 1. `raw.company_people_snapshots` (append-only)

Stores every person record from every snapshot pull.

```sql
CREATE TABLE raw.company_people_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Batch tracking
    snapshot_batch_id TEXT NOT NULL,
    snapshot_date DATE NOT NULL,

    -- Company identifier
    linkedin_company_url TEXT NOT NULL,
    company_domain TEXT,

    -- Person identifier
    linkedin_url TEXT NOT NULL,

    -- Full payload
    raw_payload JSONB NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_people_snapshots_batch ON raw.company_people_snapshots(snapshot_batch_id);
CREATE INDEX idx_people_snapshots_company ON raw.company_people_snapshots(linkedin_company_url);
CREATE INDEX idx_people_snapshots_date ON raw.company_people_snapshots(snapshot_date);
```

### 2. `reference.snapshot_batches` (tracks each pull)

Registry of completed snapshot batches.

```sql
CREATE TABLE reference.snapshot_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    snapshot_batch_id TEXT UNIQUE NOT NULL,
    linkedin_company_url TEXT NOT NULL,
    company_domain TEXT,
    snapshot_date DATE NOT NULL,
    person_count INTEGER,

    -- Processing status
    diff_processed BOOLEAN DEFAULT FALSE,
    diff_processed_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_snapshot_batches_company ON reference.snapshot_batches(linkedin_company_url);
CREATE INDEX idx_snapshot_batches_date ON reference.snapshot_batches(snapshot_date);
```

### 3. `detected.person_company_changes` (the signals)

Detected hires and departures.

```sql
CREATE TABLE detected.person_company_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Company
    linkedin_company_url TEXT NOT NULL,
    company_domain TEXT,

    -- Person
    linkedin_url TEXT NOT NULL,
    person_name TEXT,
    person_title TEXT,

    -- Change info
    change_type TEXT NOT NULL,  -- 'hired' | 'departed'

    -- Snapshot references
    snapshot_before_batch_id TEXT,
    snapshot_after_batch_id TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_person_changes_company ON detected.person_company_changes(linkedin_company_url);
CREATE INDEX idx_person_changes_type ON detected.person_company_changes(change_type);
CREATE INDEX idx_person_changes_detected ON detected.person_company_changes(detected_at);
CREATE INDEX idx_person_changes_person ON detected.person_company_changes(linkedin_url);
```

---

## Processing Flow

### Clay Workflow (scheduled weekly)

```
1. Find People for Company X
2. For each person found:
   └── POST to ingest-company-people-snapshot
       - snapshot_batch_id: "{linkedin_company_url}_{date}"
       - linkedin_company_url
       - company_domain
       - linkedin_url
       - raw_payload: {...}
3. [Wait X hours OR schedule delayed action]
4. POST to detect-company-people-changes
   - snapshot_batch_id: "{linkedin_company_url}_{date}"
   - linkedin_company_url
```

### Ingest Endpoint

`POST /ingest-company-people-snapshot`

```json
{
  "snapshot_batch_id": "https://linkedin.com/company/acme_2026-01-30",
  "linkedin_company_url": "https://linkedin.com/company/acme",
  "company_domain": "acme.com",
  "linkedin_url": "https://linkedin.com/in/john-doe",
  "raw_payload": {...}
}
```

- Stores to `raw.company_people_snapshots`
- Upserts batch info to `reference.snapshot_batches` (increment person_count)

### Detect Endpoint

`POST /detect-company-people-changes`

```json
{
  "snapshot_batch_id": "https://linkedin.com/company/acme_2026-01-30",
  "linkedin_company_url": "https://linkedin.com/company/acme"
}
```

Processing logic:
1. Get current batch's people (by snapshot_batch_id)
2. Get previous batch's people (same linkedin_company_url, earlier date)
3. Compare sets by linkedin_url:
   - In previous but not current → `departed`
   - In current but not previous → `hired`
4. Write changes to `detected.person_company_changes`
5. Mark batch as processed in `reference.snapshot_batches`

---

## Scale Considerations

| Volume | Approach |
|--------|----------|
| 1k companies/week | Single endpoint, simple queries |
| 10k companies/week | Add indexes, optimize queries |
| 100k+ companies/week | Partition tables by date, parallel detection workers |

---

## Files (to be created)

- Ingest: `modal-mcp-server/src/ingest/company_people_snapshot.py`
- Detection: `modal-mcp-server/src/detect/company_people_changes.py`
- Migration: `supabase/migrations/YYYYMMDD_company_people_snapshots.sql`
- Docs: `docs/modal/workflows/company-people-snapshot-diff.md`

---

## Open Items

- [ ] Confirm snapshot_batch_id format with Clay workflow
- [ ] Determine delay timing between ingest and detect (X hours)
- [ ] Consider adding client_domain for multi-tenant tracking
- [ ] Future: Connect detected changes to core.people / core.companies
