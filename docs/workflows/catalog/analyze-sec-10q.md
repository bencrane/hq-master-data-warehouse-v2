# analyze_sec_10q

> **Last Updated:** 2026-02-03

## Purpose

Analyzes an SEC 10-Q quarterly report using Gemini and returns a sales-ready briefing.

## Use Case

You have a 10-Q document URL (from `fetch_sec_filings`). Send it to Gemini for analysis to get:
- Quarter highlights
- Financial performance
- Recent developments
- Challenges or concerns
- Sales talking points

## Endpoints

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-analyze-sec-10q.modal.run
```

**HQ API (wrapper):** Not yet implemented

## Expected Payload

```json
{
  "document_url": "https://www.sec.gov/Archives/edgar/data/1835830/000183583025000110/kvyo-20250930.htm",
  "domain": "klaviyo.com",
  "company_name": "Klaviyo, Inc."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| document_url | string | Yes | SEC filing document URL |
| domain | string | No | Company domain for context |
| company_name | string | No | Company name for context |

## Response

```json
{
  "success": true,
  "filing_type": "10-Q",
  "document_url": "https://www.sec.gov/...",
  "domain": "klaviyo.com",
  "company_name": "Klaviyo, Inc.",
  "analysis": "## Quarter Highlights\n..."
}
```

## Prompt Configuration

Edit prompts in `modal-functions/src/prompts/sec_filings.py` to iterate on output.

## File Locations

| File | Purpose |
|------|---------|
| `modal-functions/src/ingest/sec_filing_analysis.py` | Modal function |
| `modal-functions/src/prompts/sec_filings.py` | Prompt templates |

## Cost

Gemini API cost + Modal compute time.
