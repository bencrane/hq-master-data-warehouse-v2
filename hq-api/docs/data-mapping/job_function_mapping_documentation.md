# Job Function Mapping Documentation

## Overview

This document describes the job function mapping system implemented for person records in the data warehouse. The system maps raw job titles to standardized job function categories.

## Architecture

### Lookup Table

**Table:** `reference.job_title_lookup`

| Column | Type | Description |
|--------|------|-------------|
| `latest_title` | TEXT | Raw job title (the key to match against) |
| `cleaned_job_title` | TEXT | Standardized/cleaned version of the title |
| `seniority_level` | TEXT | Seniority category (C-suite, VP, Director, Manager, Senior, Entry, etc.) |
| `job_function` | TEXT | Functional department/category |

### Person Tables with `matched_job_function`

The following tables have the `matched_job_function` column populated from the lookup:

| Table | Title Column | Description |
|-------|--------------|-------------|
| `extracted.person_discovery` | `latest_title` | Main person discovery table |
| `extracted.person_profile` | `latest_title` | Person profile data |
| `extracted.person_experience` | `title` | Work history/experience records |
| `extracted.salesnav_scrapes_person` | `job_title` | Sales Navigator scraped persons |

## Job Function Taxonomy

The following job functions are defined (22 categories):

| Job Function | Description |
|--------------|-------------|
| `Administrative` | Admin assistants, office managers |
| `Business Development` | BD managers, partnership roles, corporate development |
| `Customer Success` | CSMs, customer experience, customer advocacy |
| `Design` | Product designers, UX/UI designers |
| `Education` | Training, learning & development |
| `Engineering` | Software engineers, data scientists, TPMs, CTOs |
| `Finance` | CFOs, accountants, financial analysts, procurement |
| `General` | Generic titles without clear function (VP, Director, Manager) |
| `Growth` | Growth managers, growth specialists |
| `Healthcare` | Healthcare-specific roles |
| `Human Resources` | HR, People, Talent, Benefits |
| `Information Technology (IT)` | IT analysts, IT support |
| `Investment & Advisory` | Board members, investors, advisors |
| `Legal and Compliance` | Legal counsel, legal operations |
| `Marketing` | Marketing managers, CMOs, SEO, digital marketing |
| `Operations` | COOs, operations managers, program managers |
| `Product` | Product managers, CPOs |
| `Public Relations` | PR managers, communications |
| `Recruiting` | Recruiters, talent acquisition |
| `Revenue Operations` | RevOps roles |
| `Sales` | AEs, SDRs, sales directors, CEOs/Founders (mapped to Sales) |
| `Security, Risk, & Compliance` | CISOs, security researchers, risk managers, compliance officers |
| `Support` | Customer support, client support |

## Mapping Process

### How the Mapping Works

1. **JOIN on raw title:** Person tables are joined to the lookup table on the raw title field
2. **Pull job_function:** When a match is found, `job_function` is copied to `matched_job_function`
3. **NULL handling:** Only non-NULL, non-empty job_function values are copied

### Standard UPDATE Query Pattern

```sql
UPDATE extracted.person_discovery p
SET matched_job_function = l.job_function
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_job_function IS NULL
  AND l.job_function IS NOT NULL AND l.job_function != '';
```

### Adding New Titles to Lookup

```sql
INSERT INTO reference.job_title_lookup (latest_title, cleaned_job_title, job_function)
SELECT v.latest_title, v.cleaned_job_title, v.job_function
FROM (VALUES
  ('Software Engineer', 'Software Engineer', 'Engineering'),
  ('software engineer', 'Software Engineer', 'Engineering')
) AS v(latest_title, cleaned_job_title, job_function)
WHERE NOT EXISTS (
  SELECT 1 FROM reference.job_title_lookup l
  WHERE l.latest_title = v.latest_title
);
```

## Key Decisions

### CEO/Founder Titles -> Sales
CEO, Founder, President, and Co-founder titles are mapped to **Sales** function. Rationale: In the context of this database (likely B2B sales/marketing), founders are often the primary sales drivers.

### Generic Titles -> General
Titles like "Vice President", "Director", "Manager" without a specific domain are mapped to **General** as a last resort.

### Security Renamed
Original "Security" function was renamed to **"Security, Risk, & Compliance"** to be more comprehensive and include risk managers and compliance officers.

## Current Coverage Statistics

As of the last mapping run:

### Lookup Table
- Total entries: 21,566
- With job_function: ~14,600 (67.5%)
- Missing job_function: ~7,000

### Person Tables

| Table | Total | Has matched_job_function | % |
|-------|-------|--------------------------|---|
| person_discovery | 1,194,439 | ~568,000 | ~47.5% |
| person_profile | 153,543 | ~89,500 | ~58% |
| person_experience | 1,239,481 | ~475,000 | ~38% |
| salesnav_scrapes_person | 113,334 | ~26,200 | ~23% |

## Finding Unmapped Titles

To find common titles that need to be added to the lookup:

```sql
-- Titles in person tables but NOT in lookup
SELECT p.latest_title, COUNT(*) as cnt
FROM extracted.person_discovery p
LEFT JOIN reference.job_title_lookup l ON p.latest_title = l.latest_title
WHERE p.matched_job_function IS NULL
  AND l.latest_title IS NULL
GROUP BY p.latest_title
ORDER BY cnt DESC
LIMIT 50;
```

To find titles IN lookup but missing job_function:

```sql
SELECT cleaned_job_title, COUNT(*) as cnt
FROM reference.job_title_lookup
WHERE job_function IS NULL
  AND cleaned_job_title IS NOT NULL AND cleaned_job_title != ''
GROUP BY cleaned_job_title
ORDER BY cnt DESC
LIMIT 50;
```

## Related Fields

### Pre-existing Fields (keyword-based)
The person tables also have `keyword_job_function` which was populated using regex pattern matching. The `matched_job_function` field uses the lookup table approach for more precise matching.

### Seniority (Pending)
The `matched_seniority` column has been added to person tables but not yet populated. It will use `job_title_lookup.seniority_level`.

### Other Matched Fields
- `matched_cleaned_job_title` - Standardized job title from lookup
- `matched_industry` - On company tables, from `reference.industry_lookup`

## Maintenance

### Adding New Job Functions
1. Decide on the new function name
2. Update lookup entries: `UPDATE reference.job_title_lookup SET job_function = 'New Function' WHERE ...`
3. Re-run mapping on person tables

### Renaming Job Functions
```sql
-- Update lookup
UPDATE reference.job_title_lookup
SET job_function = 'New Name'
WHERE job_function = 'Old Name';

-- Update all person tables
UPDATE extracted.person_discovery
SET matched_job_function = 'New Name'
WHERE matched_job_function = 'Old Name';
-- (repeat for other person tables)
```
