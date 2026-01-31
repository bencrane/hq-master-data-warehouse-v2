# TAM Demo Product - Vision & Requirements

## Overview

Build a live/async TAM (Total Addressable Market) mapping tool that turns sales calls into product delivery. Instead of a traditional sales pitch, prospects see their actual TAM materialize in real-time during the call. What they see is what they buy—no black box.

## Core Concept

The product serves two use cases:

### 1. Live Demo / Onboarding Call
- Get on a call with a prospect (or do async)
- Input their targeting criteria in real-time using the UI
- They watch their TAM build live—companies, people, signals
- Save the parameters when done
- They pay for exactly what they saw
- Post-payment: expand with their CRM data for enrichment

### 2. Outbound Teaser Links
- I have a list of companies I want to sell to
- For each target company, generate a teaser link
- Link shows: "Here are 50 records for [Company X], 500 more available"
- Drives inbound interest without giving away the full dataset

## User Flows

### Flow A: Live Call → Sale
```
1. Start call with prospect
2. Open TAM builder UI
3. Input criteria together:
   - Past employer domains (e.g., "salesforce.com", "hubspot.com")
   - Job functions (e.g., "Sales", "Marketing")
   - Seniority levels (e.g., "Director", "VP")
   - Company size, industry, location, etc.
4. Results populate live as criteria are set
5. Prospect sees their TAM—real data, real people
6. Click "Save" → criteria stored in DB
7. Prospect pays
8. They get access to full dataset via their saved search
```

### Flow B: Outbound Teaser
```
1. I select a target company (e.g., "Acme Corp")
2. I define criteria that would be relevant to them
3. System generates a shareable link
4. Link shows partial data:
   - 50 fully visible records
   - "500+ more records available" (obscured)
5. Prospect clicks link, sees the teaser
6. They reach out → becomes Flow A
```

### Flow C: Saved Search Access
```
1. Client has paid and has a saved search ID
2. They (or their tools) hit the API:
   GET /api/saved-searches/{id}/leads
3. Returns the full dataset matching their saved criteria
4. Can re-query anytime—data updates as our DB updates
```

## Technical Requirements

### Database Layer (PostgreSQL)

**New table: `core.saved_searches`**
```sql
CREATE TABLE core.saved_searches (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT,
    criteria JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    owner_id UUID,           -- client identifier
    owner_email TEXT,        -- for easy lookup
    is_public BOOLEAN DEFAULT false,
    reveal_limit INT DEFAULT 50,  -- how many records to show in teaser
    status TEXT DEFAULT 'active'  -- active, expired, converted
);
```

**New function: `core.get_leads_for_saved_search()`**
- Input: `search_id UUID`, `p_limit INT`, `p_offset INT`, `p_reveal BOOLEAN`
- Reads criteria from saved_searches table
- Applies criteria to leads query (reuses existing filter logic)
- If `p_reveal = false`, returns limited fields (teaser mode)
- Returns typed TABLE matching lead structure

**Existing function needed: `core.get_leads_by_past_employer()`**
- This is Stage 4 blocker—must be built first
- Input: `domain_list TEXT[]`, filters, limit, offset
- Joins person_work_history → leads
- Returns leads who previously worked at specified companies

### API Layer (FastAPI)

**New endpoints:**

```
POST /api/saved-searches
- Creates a new saved search
- Body: { name, criteria, owner_email }
- Returns: { id, name, criteria, created_at }

GET /api/saved-searches/{id}
- Returns saved search metadata + criteria
- Does NOT return leads (separate endpoint)

GET /api/saved-searches/{id}/leads
- Returns leads matching the saved criteria
- Query params: limit, offset, reveal (boolean)
- If reveal=false, returns obscured/limited data

GET /api/saved-searches/{id}/preview
- Returns teaser: N visible + count of obscured
- Used for shareable teaser links

DELETE /api/saved-searches/{id}
- Soft delete (set status = 'deleted')
```

**Link generation:**
- Shareable link format: `https://app.domain.com/tam/{saved_search_id}`
- Frontend handles rendering based on reveal permissions

### Frontend Requirements

**TAM Builder UI:**
- Filter controls for all criteria (job function, seniority, domains, etc.)
- Live results table that updates as filters change
- "Save Search" button
- Works on call = real-time, low latency

**Teaser View:**
- Shows N visible records in full
- Shows "X more records available" for obscured
- CTA to contact / purchase

**Client Dashboard (future):**
- List of their saved searches
- Ability to re-run / export
- Usage stats

## Criteria Schema (JSONB)

```json
{
  "past_employer_domains": ["salesforce.com", "hubspot.com"],
  "job_functions": ["Sales", "Marketing"],
  "seniorities": ["Director", "VP", "C-Suite"],
  "industries": ["Software", "SaaS"],
  "employee_ranges": ["51-200", "201-500"],
  "person_country": "United States",
  "person_state": "California",
  "vc_name": "Sequoia Capital",
  "started_within_days": 90,
  "promoted_within_days": 180
}
```

All fields optional. Null/missing = no filter on that dimension.

## Architecture Fit

This design follows the existing architecture principles:

1. **Database owns business logic** — `get_leads_for_saved_search()` function does the work
2. **Thin API layer** — Endpoints just call the function, shape response
3. **Views for simple, functions for complex** — Saved search execution is complex (dynamic criteria), so it's a function
4. **Explicit column selection** — Teaser mode returns subset of columns
5. **Consistent response shapes** — Same `{ data, meta }` structure

## Implementation Order

1. **Unblock Stage 4** — Build `core.get_leads_by_past_employer()` function
2. **Create saved_searches table** — Schema + indexes
3. **Create `get_leads_for_saved_search()` function** — Core query logic
4. **Build API endpoints** — CRUD for saved searches + leads retrieval
5. **Build TAM builder UI** — Filter controls + live results
6. **Build teaser view** — Shareable link rendering
7. **Deploy to Railway** — Stage 5

## Success Criteria

- [ ] Can input criteria on a live call and see results populate
- [ ] Can save criteria and get a unique ID/link
- [ ] Can retrieve full leads for a saved search via API
- [ ] Can generate teaser link showing partial data
- [ ] Any frontend can query saved searches via API
- [ ] Latency < 2s for typical queries during live demo