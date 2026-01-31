# Seniority Mapping Plan

## Objective

Populate `matched_seniority` on all person tables using the `seniority_level` field from `reference.job_title_lookup`.

---

## Current State

### Person Tables (already have `matched_seniority` column added)

| Table | Title Column | Status |
|-------|--------------|--------|
| `extracted.person_discovery` | `latest_title` | Column added, not populated |
| `extracted.person_profile` | `latest_title` | Column added, not populated |
| `extracted.person_experience` | `title` | Column added, not populated |
| `extracted.salesnav_scrapes_person` | `job_title` | Column added, not populated |

### Lookup Table Coverage

Need to check: How many entries in `job_title_lookup` have `seniority_level` populated?

---

## Seniority Taxonomy

Existing seniority levels in lookup table:

| Seniority Level | Description |
|-----------------|-------------|
| C-suite | CEO, CFO, CTO, CMO, CIO, COO, etc. |
| VP | Vice Presidents |
| Director | Directors |
| Head | Head of X roles |
| Manager | Managers |
| Senior | Senior individual contributors |
| Entry | Entry-level roles |
| Partner | Partners (law, consulting, VC) |
| Owner | Business owners |
| Freelance | Freelancers, contractors |
| Intern | Interns |
| Assistant | Assistants |

---

## Execution Plan

### Step 1: Check Lookup Table Seniority Coverage

```sql
SELECT
  COUNT(*) as total,
  COUNT(seniority_level) as has_seniority,
  COUNT(*) - COUNT(seniority_level) as missing_seniority,
  ROUND(COUNT(seniority_level)::numeric / COUNT(*) * 100, 1) as pct
FROM reference.job_title_lookup;
```

### Step 2: Populate Missing Seniority in Lookup Table

For entries missing `seniority_level`, use pattern matching on `cleaned_job_title`:

```sql
-- C-suite
UPDATE reference.job_title_lookup
SET seniority_level = 'C-suite'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\m(CEO|CFO|CTO|CMO|CIO|COO|CHRO|Chief)\M';

-- VP
UPDATE reference.job_title_lookup
SET seniority_level = 'VP'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\m(Vice President|VP)\M';

-- Director
UPDATE reference.job_title_lookup
SET seniority_level = 'Director'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\mDirector\M';

-- Head
UPDATE reference.job_title_lookup
SET seniority_level = 'Head'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\mHead of\M';

-- Manager
UPDATE reference.job_title_lookup
SET seniority_level = 'Manager'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\mManager\M';

-- Senior
UPDATE reference.job_title_lookup
SET seniority_level = 'Senior'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\mSenior\M';

-- Intern
UPDATE reference.job_title_lookup
SET seniority_level = 'Intern'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\mIntern\M';

-- Entry (Associate, Coordinator, Specialist without Senior)
UPDATE reference.job_title_lookup
SET seniority_level = 'Entry'
WHERE seniority_level IS NULL
  AND cleaned_job_title ~* '\m(Associate|Coordinator|Specialist|Analyst)\M'
  AND cleaned_job_title !~* '\mSenior\M';
```

### Step 3: Populate matched_seniority on Person Tables

```sql
-- person_discovery
UPDATE extracted.person_discovery p
SET matched_seniority = l.seniority_level
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_seniority IS NULL
  AND l.seniority_level IS NOT NULL AND l.seniority_level != '';

-- person_profile
UPDATE extracted.person_profile p
SET matched_seniority = l.seniority_level
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_seniority IS NULL
  AND l.seniority_level IS NOT NULL AND l.seniority_level != '';

-- person_experience
UPDATE extracted.person_experience p
SET matched_seniority = l.seniority_level
FROM reference.job_title_lookup l
WHERE p.title = l.latest_title
  AND p.matched_seniority IS NULL
  AND l.seniority_level IS NOT NULL AND l.seniority_level != '';

-- salesnav_scrapes_person
UPDATE extracted.salesnav_scrapes_person p
SET matched_seniority = l.seniority_level
FROM reference.job_title_lookup l
WHERE p.job_title = l.latest_title
  AND p.matched_seniority IS NULL
  AND l.seniority_level IS NOT NULL AND l.seniority_level != '';
```

### Step 4: Check Coverage & Identify Gaps

```sql
-- Check final coverage
SELECT
  'person_discovery' as table_name,
  COUNT(*) as total,
  COUNT(matched_seniority) as has_seniority,
  ROUND(COUNT(matched_seniority)::numeric / COUNT(*) * 100, 1) as pct
FROM extracted.person_discovery
UNION ALL
SELECT 'person_profile', COUNT(*), COUNT(matched_seniority),
  ROUND(COUNT(matched_seniority)::numeric / COUNT(*) * 100, 1)
FROM extracted.person_profile
UNION ALL
SELECT 'person_experience', COUNT(*), COUNT(matched_seniority),
  ROUND(COUNT(matched_seniority)::numeric / COUNT(*) * 100, 1)
FROM extracted.person_experience
UNION ALL
SELECT 'salesnav_scrapes_person', COUNT(*), COUNT(matched_seniority),
  ROUND(COUNT(matched_seniority)::numeric / COUNT(*) * 100, 1)
FROM extracted.salesnav_scrapes_person;
```

### Step 5: Fill Remaining Gaps

For high-frequency titles still missing seniority:

```sql
-- Find common titles missing seniority in lookup
SELECT cleaned_job_title, COUNT(*) as cnt
FROM reference.job_title_lookup
WHERE seniority_level IS NULL
  AND cleaned_job_title IS NOT NULL
GROUP BY cleaned_job_title
ORDER BY cnt DESC
LIMIT 50;
```

Manually categorize remaining high-frequency titles.

---

## Validation

After completion, verify:
1. Lookup table seniority coverage > 80%
2. Person tables matched_seniority coverage > 50%
3. Distribution of seniority levels is reasonable

---

## Notes

- Seniority is inferred from job title, not tenure or experience
- Some titles may be ambiguous (e.g., "Consultant" could be senior or entry)
- Founder/CEO titles already mapped to C-suite in many cases
- The `keyword_seniority` field exists but uses regex; `matched_seniority` uses lookup table for precision

---

*Created: 2026-01-25*
