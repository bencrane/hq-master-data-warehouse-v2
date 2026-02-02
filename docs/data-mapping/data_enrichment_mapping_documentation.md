# Data Enrichment & Mapping Documentation

## Overview

This document describes the data enrichment and mapping systems implemented in this session for standardizing person and company records in the data warehouse. The system uses lookup tables to map raw values to standardized/cleaned values.

---

## 1. Industry Mapping (Companies)

### Lookup Table

**Table:** `reference.industry_lookup`

| Column | Type | Description |
|--------|------|-------------|
| `industry_raw` | TEXT | Raw industry value (the key to match against) |
| `industry_cleaned` | TEXT | Standardized industry name |

### Company Tables with `matched_industry`

| Table | Industry Column | Description |
|-------|-----------------|-------------|
| `extracted.company_discovery` | `industry` | Company discovery records |
| `extracted.company_firmographics` | `industry` | Company firmographic data |
| `extracted.salesnav_scrapes_companies` | `industries` | Sales Navigator scraped companies |

### Mapping Query Pattern

```sql
UPDATE extracted.company_discovery c
SET matched_industry = l.industry_cleaned
FROM reference.industry_lookup l
WHERE c.industry = l.industry_raw
  AND c.matched_industry IS NULL
  AND l.industry_cleaned IS NOT NULL AND l.industry_cleaned != '';
```

### Adding New Industries

```sql
INSERT INTO reference.industry_lookup (industry_raw, industry_cleaned)
SELECT v.industry_raw, v.industry_cleaned
FROM (VALUES
  ('Computer Software', 'Software'),
  ('computer software', 'Software')
) AS v(industry_raw, industry_cleaned)
WHERE NOT EXISTS (
  SELECT 1 FROM reference.industry_lookup l
  WHERE l.industry_raw = v.industry_raw
);
```

---

## 2. Job Title Mapping (People)

### Lookup Table

**Table:** `reference.job_title_lookup`

| Column | Type | Description |
|--------|------|-------------|
| `latest_title` | TEXT | Raw job title (the key to match against) |
| `cleaned_job_title` | TEXT | Standardized/cleaned job title |
| `seniority_level` | TEXT | Seniority category |
| `job_function` | TEXT | Functional department/category |

### Person Tables with Matched Fields

| Table | Title Column | Matched Fields |
|-------|--------------|----------------|
| `extracted.person_discovery` | `latest_title` | `matched_cleaned_job_title`, `matched_job_function`, `matched_seniority` |
| `extracted.person_profile` | `latest_title` | `matched_cleaned_job_title`, `matched_job_function`, `matched_seniority` |
| `extracted.person_experience` | `title` | `matched_cleaned_job_title`, `matched_job_function`, `matched_seniority` |
| `extracted.salesnav_scrapes_person` | `job_title` | `matched_cleaned_job_title`, `matched_job_function`, `matched_seniority` |

### Mapping Query Pattern

```sql
-- Map cleaned job title
UPDATE extracted.person_discovery p
SET matched_cleaned_job_title = l.cleaned_job_title
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_cleaned_job_title IS NULL
  AND l.cleaned_job_title IS NOT NULL AND l.cleaned_job_title != '';

-- Map job function
UPDATE extracted.person_discovery p
SET matched_job_function = l.job_function
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_job_function IS NULL
  AND l.job_function IS NOT NULL AND l.job_function != '';

-- Map seniority
UPDATE extracted.person_discovery p
SET matched_seniority = l.seniority_level
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_seniority IS NULL
  AND l.seniority_level IS NOT NULL AND l.seniority_level != '';
```

### Adding New Job Titles

```sql
INSERT INTO reference.job_title_lookup (latest_title, cleaned_job_title, seniority_level, job_function)
SELECT v.latest_title, v.cleaned_job_title, v.seniority_level, v.job_function
FROM (VALUES
  ('Software Engineer', 'Software Engineer', 'Senior', 'Engineering'),
  ('software engineer', 'Software Engineer', 'Senior', 'Engineering'),
  ('Sr. Software Engineer', 'Senior Software Engineer', 'Senior', 'Engineering')
) AS v(latest_title, cleaned_job_title, seniority_level, job_function)
WHERE NOT EXISTS (
  SELECT 1 FROM reference.job_title_lookup l
  WHERE l.latest_title = v.latest_title
);
```

### Important: Case Sensitivity

The lookup matching is **case-sensitive**. To ensure matches, add both common case variations:
- `Software Engineer`
- `software engineer`
- `SOFTWARE ENGINEER`

### Duplicate Entry Prevention

The lookup table had issues with duplicate entries where some had NULL cleaned_job_title. This was fixed by:

1. Adding filter to UPDATE queries:
```sql
AND l.cleaned_job_title IS NOT NULL AND l.cleaned_job_title != ''
```

2. Deleting bad rows:
```sql
DELETE FROM reference.job_title_lookup
WHERE cleaned_job_title IS NULL OR cleaned_job_title = '';
```

---

## 3. Job Function Taxonomy

The following 22 job function categories are defined:

| Job Function | Description | Example Titles |
|--------------|-------------|----------------|
| `Administrative` | Admin assistants, office managers | Executive Assistant, Office Manager |
| `Business Development` | BD managers, partnerships | BD Manager, Head of Partnerships |
| `Customer Success` | CSMs, customer experience | CSM, Director of Customer Experience |
| `Design` | Product/UX/UI designers | Product Designer, UX Designer |
| `Education` | Training, L&D | Training Manager, L&D Specialist |
| `Engineering` | Software, data, TPMs, CTOs | Software Engineer, CTO, Data Scientist |
| `Finance` | CFOs, accountants, analysts | CFO, Financial Analyst, Controller |
| `General` | Generic titles without function | Vice President, Director, Manager |
| `Growth` | Growth specialists | Growth Manager, VP of Growth |
| `Healthcare` | Healthcare-specific | Healthcare Consultant |
| `Human Resources` | HR, People, Talent | CHRO, HR Manager, Recruiter |
| `Information Technology (IT)` | IT analysts, support | IT Manager, IT Support Engineer |
| `Investment & Advisory` | Board, investors, advisors | Board Member, Investor, Advisor |
| `Legal and Compliance` | Legal counsel, ops | General Counsel, Legal Ops |
| `Marketing` | Marketing, CMOs, SEO | CMO, Marketing Manager, SEO Specialist |
| `Operations` | COOs, ops managers | COO, Operations Manager |
| `Product` | Product managers, CPOs | CPO, Product Manager |
| `Public Relations` | PR, communications | PR Manager, Comms Director |
| `Recruiting` | Recruiters, TA | Recruiter, TA Manager |
| `Revenue Operations` | RevOps | RevOps Manager |
| `Sales` | AEs, SDRs, CEOs/Founders | AE, SDR, CEO, Founder |
| `Security, Risk, & Compliance` | CISOs, risk, compliance | CISO, Risk Manager, Compliance Officer |
| `Support` | Customer support | Support Engineer, Support Manager |

### Key Decisions

- **CEO/Founder -> Sales**: Founder, CEO, President titles are mapped to Sales (rationale: in B2B context, founders drive sales)
- **Generic -> General**: Titles like "Vice President", "Director" without specific domain go to General
- **Security expanded**: Original "Security" renamed to "Security, Risk, & Compliance" to include risk and compliance roles

---

## 4. Seniority Taxonomy

The `seniority_level` field uses these categories:

| Seniority Level | Description |
|-----------------|-------------|
| `C-suite` | CEO, CFO, CTO, CMO, etc. |
| `VP` | Vice Presidents |
| `Director` | Directors |
| `Head` | Head of X roles |
| `Manager` | Managers |
| `Senior` | Senior individual contributors |
| `Entry` | Entry-level roles |
| `Partner` | Partners (law, consulting, VC) |
| `Owner` | Business owners |
| `Freelance` | Freelancers, contractors |
| `Intern` | Interns |
| `Assistant` | Assistants |

---

## 5. Location Mapping (People)

### Lookup Table

**Table:** `reference.clay_find_people_location_lookup`

Person tables have these location fields:
- `city`, `state`, `country` - raw values
- `matched_city`, `matched_state`, `matched_country` - from lookup
- `has_city`, `has_state`, `has_country` - boolean flags

### Company Location

**Table:** `reference.clay_find_companies_location_lookup`

Company tables have similar location fields populated from this lookup.

---

## 6. Pre-existing Keyword Fields

Before the lookup-based approach, keyword fields were populated using regex patterns:

### Person Tables
- `keyword_job_function` - populated via regex on latest_title
- `keyword_seniority` - populated via regex on latest_title

These use patterns like:
```sql
-- Example: Set keyword_seniority for C-suite
UPDATE extracted.person_discovery
SET keyword_seniority = 'C-suite'
WHERE latest_title ~* '\m(CEO|CFO|CTO|CMO|CIO|COO|Chief)\M';
```

The `matched_*` fields (from lookup tables) are more precise than the `keyword_*` fields (from regex).

---

## 7. Current Coverage Statistics

### Job Title Lookup Table
- Total entries: ~21,600
- With job_function: ~14,600 (67.5%)
- With seniority_level: ~17,300 (80%)

### Person Tables - Job Function Coverage

| Table | Total | Has matched_job_function | % |
|-------|-------|--------------------------|---|
| person_discovery | 1,194,439 | ~568,000 | ~47.5% |
| person_profile | 153,543 | ~89,500 | ~58% |
| person_experience | 1,239,481 | ~475,000 | ~38% |
| salesnav_scrapes_person | 113,334 | ~26,200 | ~23% |

---

## 8. Finding Unmapped Records

### Titles Not in Lookup Table

```sql
SELECT p.latest_title, COUNT(*) as cnt
FROM extracted.person_discovery p
LEFT JOIN reference.job_title_lookup l ON p.latest_title = l.latest_title
WHERE p.matched_job_function IS NULL
  AND l.latest_title IS NULL
GROUP BY p.latest_title
ORDER BY cnt DESC
LIMIT 50;
```

### Titles in Lookup but Missing job_function

```sql
SELECT cleaned_job_title, COUNT(*) as cnt
FROM reference.job_title_lookup
WHERE job_function IS NULL
  AND cleaned_job_title IS NOT NULL AND cleaned_job_title != ''
GROUP BY cleaned_job_title
ORDER BY cnt DESC
LIMIT 50;
```

### Industries Not in Lookup Table

```sql
SELECT c.industry, COUNT(*) as cnt
FROM extracted.company_discovery c
LEFT JOIN reference.industry_lookup l ON c.industry = l.industry_raw
WHERE c.matched_industry IS NULL
  AND l.industry_raw IS NULL
  AND c.industry IS NOT NULL
GROUP BY c.industry
ORDER BY cnt DESC
LIMIT 50;
```

---

## 9. Maintenance Procedures

### Adding New Job Function Category

1. Update lookup entries:
```sql
UPDATE reference.job_title_lookup
SET job_function = 'New Category'
WHERE cleaned_job_title IN ('Title 1', 'Title 2', ...);
```

2. Re-run mapping on person tables:
```sql
UPDATE extracted.person_discovery p
SET matched_job_function = l.job_function
FROM reference.job_title_lookup l
WHERE p.latest_title = l.latest_title
  AND p.matched_job_function IS NULL
  AND l.job_function IS NOT NULL;
```

### Renaming a Job Function

```sql
-- Update lookup
UPDATE reference.job_title_lookup
SET job_function = 'New Name'
WHERE job_function = 'Old Name';

-- Update all person tables
UPDATE extracted.person_discovery SET matched_job_function = 'New Name' WHERE matched_job_function = 'Old Name';
UPDATE extracted.person_profile SET matched_job_function = 'New Name' WHERE matched_job_function = 'Old Name';
UPDATE extracted.person_experience SET matched_job_function = 'New Name' WHERE matched_job_function = 'Old Name';
UPDATE extracted.salesnav_scrapes_person SET matched_job_function = 'New Name' WHERE matched_job_function = 'Old Name';
```

---

## 10. Schema Summary

### Reference Tables (Lookups)

| Table | Purpose |
|-------|---------|
| `reference.job_title_lookup` | Job title → cleaned title, seniority, function |
| `reference.industry_lookup` | Raw industry → cleaned industry |
| `reference.clay_find_people_location_lookup` | Person location parsing |
| `reference.clay_find_companies_location_lookup` | Company location parsing |
| `reference.salesnav_location_lookup` | SalesNav location lookup |

### Extracted Tables (Person)

| Table | Key Matched Fields |
|-------|-------------------|
| `extracted.person_discovery` | matched_cleaned_job_title, matched_job_function, matched_seniority |
| `extracted.person_profile` | matched_cleaned_job_title, matched_job_function, matched_seniority |
| `extracted.person_experience` | matched_cleaned_job_title, matched_job_function, matched_seniority |
| `extracted.salesnav_scrapes_person` | matched_cleaned_job_title, matched_job_function, matched_seniority |

### Extracted Tables (Company)

| Table | Key Matched Fields |
|-------|-------------------|
| `extracted.company_discovery` | matched_industry |
| `extracted.company_firmographics` | matched_industry |
| `extracted.salesnav_scrapes_companies` | matched_industry |
