# fetch_sec_filings

> **Last Updated:** 2026-02-03

## Purpose

Fetches SEC EDGAR filing metadata for a public company and returns filtered, actionable filings for sales briefings. Returns document URLs that can be passed to an LLM (Gemini/Claude) for summarization.

## Use Case

A lead comes in from a public company. Before the sales call, you want a briefing:
- "They stated in their last 10-Q that..."
- "Senior VP/COO just left according to an 8-K..."
- "They announced earnings on..."

This endpoint gives you the filing metadata and document URLs. Pass the URLs to an LLM to extract insights.

## Endpoints

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-fetch-sec-filings.modal.run
```

**HQ API (wrapper):**
```
POST https://api.revenueinfra.com/run/companies/sec/filings/fetch
```

## Expected Payload

```json
{
  "domain": "apple.com"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| domain | string | Yes | Company domain (must have ticker ingested first) |

## Response

```json
{
  "success": true,
  "domain": "apple.com",
  "cik": "0000320193",
  "ticker": "AAPL",
  "company_name": "Apple Inc",
  "filings": {
    "latest_10q": {
      "filing_date": "2025-01-30",
      "report_date": "2024-12-28",
      "accession_number": "0000320193-25-000008",
      "document_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000008/aapl-20241228.htm"
    },
    "latest_10k": {
      "filing_date": "2024-11-01",
      "report_date": "2024-09-28",
      "accession_number": "0000320193-24-000123",
      "document_url": "https://www.sec.gov/Archives/edgar/data/320193/..."
    },
    "recent_8k_executive_changes": [
      {
        "filing_date": "2025-01-15",
        "items": "5.02",
        "document_url": "..."
      }
    ],
    "recent_8k_earnings": [],
    "recent_8k_material_contracts": []
  }
}
```

### Filing Types

| Filing | Description | Use For |
|--------|-------------|---------|
| 10-Q | Quarterly report | Business outlook, guidance, risks |
| 10-K | Annual report | Strategy, risk factors, business description |
| 8-K (5.02) | Executive changes | "CFO just left", officer appointments |
| 8-K (2.02) | Earnings | Earnings announcements |
| 8-K (1.01) | Material contracts | Major deals signed |

## Error Response

```json
{
  "success": false,
  "error": "No CIK found for domain 'example.com'. Run ticker ingest first.",
  "domain": "example.com"
}
```

## Prerequisites

The domain must have ticker data ingested first via `/run/companies/ticker/ingest`. This stores the SEC CIK needed to fetch filings.

## How It Works

1. Looks up CIK from `raw.company_ticker_payloads` (from prior ticker ingest)
2. Fetches from SEC Submissions API: `https://data.sec.gov/submissions/CIK{cik}.json`
3. Filters to relevant filings (latest 10-Q/10-K, recent 8-Ks with specific items)
4. Builds document URLs for each filing
5. Returns structured response

## Workflow Slug

`sec-filings-fetch`

## File Locations

| File | Purpose |
|------|---------|
| `modal-functions/src/ingest/sec_filings.py` | Modal function |
| `hq-api/routers/run.py` | HQ API wrapper |

## Integration with Clay

1. In Clay, call the HQ API endpoint with the domain
2. Get back filing URLs
3. Pass URLs to Gemini/Claude with a prompt like:
   - "Summarize this SEC filing for a sales briefing. Focus on: business outlook, challenges, executive changes, strategic priorities."

## Cost

Zero API cost - just Modal compute time and SEC (free public data).

## Notes

- SEC requires User-Agent header (handled internally)
- CIK must be 10-digit zero-padded
- Document URLs point to the primary filing document (HTML)
- 8-K items are standardized codes (5.02 = executive changes, 2.02 = earnings, etc.)
