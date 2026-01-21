# Core Companies Linking Analysis

**Date:** January 7, 2026  
**Status:** Decision Pending

---

## Current State

### Table Counts
| Table | Total Records | With LinkedIn URL |
|-------|---------------|-------------------|
| `core.companies` | 19,572 | 9,886 (50%) |
| `extracted.company_firmographics` | 41,637 | 41,637 (100%) |

### Data Sources
- **core.companies**: Populated from `raw.company_customer_claygent_payloads` (origin companies only — ~961 unique)
- **extracted.company_firmographics**: Enriched customer companies from Clay

---

## Matching Analysis (firmographics → core)

| Match Type | Count | Percentage |
|------------|-------|------------|
| Domain exact match | 9,752 | 23.4% |
| LinkedIn URL match | 9,011 | 21.6% |
| LinkedIn match but domain differs | 207 | 0.5% |
| **No match to core** | ~31,885 | **76.6%** |

---

## Domain Quality Issues

### core.companies
- 131 domains contain `/` (paths like `1800gotjunk.com/us_en`)
- 37 domains contain `?` (query strings like `23andme.com/?srsltid=...`)
- 0 with `www.` prefix

### extracted.company_firmographics
- 6 domains contain `/` (much cleaner)
- 0 with `www.` prefix

---

## The 207 Edge Cases

These are cases where LinkedIn URL matches but domain differs (e.g., `doordash.com` vs `careersatdoordash.com`).

**Recommendation:** Do NOT auto-link these. If LinkedIn URL matches but domain differs, require manual review or treat as separate entities.

---

## Two Architectural Approaches

### Approach A: Firmographics → Core (FK in firmographics)

Add `core_company_id` column to `extracted.company_firmographics` referencing `core.companies.id`.

**Pros:**
- Aligns with hub architecture (core.companies is central)
- Firmographics is "about" a core company
- Multiple firmographic records could point to same core company

**Cons:**
- 76% of firmographics would have NULL FK (no matching core company)
- Requires backfill

**Backfill logic:** Match on domain first, then LinkedIn URL as fallback (excluding the 207 edge cases).

---

### Approach B: Core → Firmographics (FK in core)

Add `firmographics_id` column to `core.companies`.

**Pros:**
- Easy to see if a core company has firmographics enrichment

**Cons:**
- Violates stated architecture (enriched tables shouldn't link sideways)
- What if multiple firmographics per company? Only one can be linked
- Creates dependency in wrong direction

---

## The Fundamental Question

**Should core.companies be populated FROM firmographics first?**

Currently:
- `core.companies` = origin companies (~961 unique from claygent)
- `firmographics` = enriched customer companies (41,637)

If `core.companies` is meant to be the central hub for ALL companies, it needs the 41k customer companies too.

### Option 1: Backfill core.companies from firmographics
1. Insert all unique domains from firmographics into core.companies
2. Then add FK from firmographics → core.companies
3. Result: core.companies becomes the master company list

### Option 2: Keep them separate
- `core.companies` = origin companies only (the companies whose customers we're tracking)
- `firmographics` = enriched data about customer companies (no FK to core)
- Relationship is implicit via domain, not explicit via FK

---

## Matching Strategy (If We Proceed with Linking)

1. **Primary match:** `firmographics.company_domain = core.companies.domain`
2. **Secondary match:** Normalized LinkedIn URL (only if domains also match OR domain is null)
3. **Never auto-match:** If LinkedIn matches but domain differs (the 207 cases)

### LinkedIn URL Normalization
```javascript
const normalize = (url) => url.toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/^www\./, '')
    .replace(/\/$/, '');
```

---

## Next Steps (When Ready)

1. Decide: Is core.companies meant to hold ALL companies or just origin companies?
2. If all companies: Backfill from firmographics first
3. Define FK direction and matching strategy
4. Clean up dirty domains (131 with paths, 37 with query strings)
5. Handle the 207 LinkedIn-match-but-domain-differs cases

