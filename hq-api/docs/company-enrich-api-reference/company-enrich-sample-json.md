# Company Enrich API Notes

## Find Similar Companies Preview Endpoint

**Endpoint:** `POST https://api.companyenrich.com/companies/similar/preview`

**Cost:** FREE (returns top 25 similar companies)

**Authentication:** Bearer token in Authorization header

### Request Structure

```json
{
  "domains": ["stripe.com"],
  "similarityWeight": 0.0,
  "countries": ["US"]
}
```

**Parameters:**
- `domains` (required): Array of domain strings to find similar companies for
- `similarityWeight` (optional): Float from -1.0 to 1.0 (default: 0.0)
  - `-1.0`: More diverse results
  - `0.0`: Balanced
  - `1.0`: More similar results
- `countries` (optional): Array of country codes to filter results (e.g., `["US"]`)

---

## Sample Payloads

### Example 1: stripe.com (US filter, 0.5 similarity weight)

**Request:**
```json
{
  "domains": ["stripe.com"],
  "similarityWeight": 0.5,
  "countries": ["US"]
}
```

**Response:**
```json
{
  "items": [
    {
      "id": "f9e9b4f4-2c3a-4b1e-9f3e-1a2b3c4d5e6f",
      "name": "Plaid",
      "domain": "plaid.com",
      "website": "https://plaid.com",
      "industry": "Financial Services",
      "description": "Plaid is a financial services company that builds technology to connect applications to users' bank accounts.",
      "keywords": ["fintech", "banking", "api", "payments"],
      "logo_url": "https://logo.clearbit.com/plaid.com"
    },
    {
      "id": "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
      "name": "Square",
      "domain": "squareup.com",
      "website": "https://squareup.com",
      "industry": "Financial Services",
      "description": "Square provides payment and point-of-sale solutions for businesses of all sizes.",
      "keywords": ["payments", "pos", "fintech", "commerce"],
      "logo_url": "https://logo.clearbit.com/squareup.com"
    }
  ],
  "metadata": {
    "scores": {
      "f9e9b4f4-2c3a-4b1e-9f3e-1a2b3c4d5e6f": 0.92,
      "a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d": 0.88
    },
    "total": 25,
    "page": 1,
    "pageSize": 25
  }
}
```

### Example 2: airbnb.com (no country filter, balanced similarity)

**Request:**
```json
{
  "domains": ["airbnb.com"],
  "similarityWeight": 0.0
}
```

**Response:**
```json
{
  "items": [
    {
      "id": "b2c3d4e5-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
      "name": "Vrbo",
      "domain": "vrbo.com",
      "website": "https://vrbo.com",
      "industry": "Travel & Tourism",
      "description": "Vrbo is an online marketplace for vacation rentals.",
      "keywords": ["vacation rentals", "travel", "hospitality", "marketplace"],
      "logo_url": "https://logo.clearbit.com/vrbo.com"
    },
    {
      "id": "c3d4e5f6-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
      "name": "Booking.com",
      "domain": "booking.com",
      "website": "https://booking.com",
      "industry": "Travel & Tourism",
      "description": "Booking.com is an online travel agency for lodging reservations.",
      "keywords": ["travel", "hotels", "booking", "reservations"],
      "logo_url": "https://logo.clearbit.com/booking.com"
    },
    {
      "id": "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
      "name": "Sonder",
      "domain": "sonder.com",
      "website": "https://sonder.com",
      "industry": "Hospitality",
      "description": "Sonder offers apartment-style accommodations for travelers.",
      "keywords": ["hospitality", "apartments", "travel", "accommodation"],
      "logo_url": "https://logo.clearbit.com/sonder.com"
    }
  ],
  "metadata": {
    "scores": {
      "b2c3d4e5-6f7a-8b9c-0d1e-2f3a4b5c6d7e": 0.95,
      "c3d4e5f6-7a8b-9c0d-1e2f-3a4b5c6d7e8f": 0.91,
      "d4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a": 0.87
    },
    "total": 25,
    "page": 1,
    "pageSize": 25
  }
}
```

### Example 3: notion.so (diverse results, similarity weight -0.5)

**Request:**
```json
{
  "domains": ["notion.so"],
  "similarityWeight": -0.5
}
```

**Response:**
```json
{
  "items": [
    {
      "id": "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
      "name": "Coda",
      "domain": "coda.io",
      "website": "https://coda.io",
      "industry": "Software",
      "description": "Coda is a doc that brings words, data, and teams together.",
      "keywords": ["productivity", "documents", "collaboration", "no-code"],
      "logo_url": "https://logo.clearbit.com/coda.io"
    },
    {
      "id": "f6a7b8c9-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
      "name": "Airtable",
      "domain": "airtable.com",
      "website": "https://airtable.com",
      "industry": "Software",
      "description": "Airtable is a cloud collaboration service that combines spreadsheets with databases.",
      "keywords": ["database", "spreadsheet", "collaboration", "no-code"],
      "logo_url": "https://logo.clearbit.com/airtable.com"
    },
    {
      "id": "a7b8c9d0-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
      "name": "Roam Research",
      "domain": "roamresearch.com",
      "website": "https://roamresearch.com",
      "industry": "Software",
      "description": "Roam Research is a note-taking tool for networked thought.",
      "keywords": ["notes", "knowledge management", "productivity", "research"],
      "logo_url": "https://logo.clearbit.com/roamresearch.com"
    }
  ],
  "metadata": {
    "scores": {
      "e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b": 0.89,
      "f6a7b8c9-0d1e-2f3a-4b5c-6d7e8f9a0b1c": 0.85,
      "a7b8c9d0-1e2f-3a4b-5c6d-7e8f9a0b1c2d": 0.78
    },
    "total": 25,
    "page": 1,
    "pageSize": 25
  }
}
```

---

## Response Structure

| Field | Type | Description |
|-------|------|-------------|
| `items` | array | Array of similar company objects |
| `items[].id` | UUID | Company Enrich internal company ID |
| `items[].name` | string | Company name |
| `items[].domain` | string | Company domain |
| `items[].website` | string | Full website URL |
| `items[].industry` | string | Industry classification |
| `items[].description` | string | Company description |
| `items[].keywords` | array | Array of keyword strings |
| `items[].logo_url` | string | URL to company logo |
| `metadata.scores` | object | Map of company_id to similarity score (0.0-1.0) |
| `metadata.total` | integer | Total results returned |
| `metadata.page` | integer | Current page number |
| `metadata.pageSize` | integer | Results per page |

---

## Implementation Notes

### Modal Endpoint

- **Batch endpoint:** `find_similar_companies_batch` - accepts array of domains, creates batch record
- **Single endpoint:** `find_similar_companies_single` - accepts single domain

### Database Tables

- `raw.company_enrich_similar_batches` - Batch tracking (for CSV uploads)
- `raw.company_enrich_similar_raw` - Raw API responses per domain
- `extracted.company_enrich_similar` - Flattened similar company results

### Secret Required

Modal secret: `companyenrich-api-key` with `COMPANYENRICH_API_KEY` environment variable

---

## Related Files

- Migration: `supabase/migrations/20260128_company_enrich_similar.sql`
- Modal endpoint: `modal-mcp-server/src/ingest/company_enrich_similar.py`
