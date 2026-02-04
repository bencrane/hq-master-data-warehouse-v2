# analyze_sec_10k

> **Last Updated:** 2026-02-03

## Purpose

Analyzes an SEC 10-K annual report using Gemini and returns a sales-ready briefing.

## Use Case

You have a 10-K document URL (from `fetch_sec_filings`). Send it to Gemini for analysis to get:
- Business overview
- Key financial metrics
- Strategic priorities
- Risk factors
- Sales talking points

## Endpoints

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-analyze-sec-10k.modal.run
```

**HQ API (wrapper):** Not yet implemented

## Expected Payload

```json
{
  "document_url": "https://www.sec.gov/Archives/edgar/data/1835830/000183583025000014/kvyo-20241231.htm",
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
  "filing_type": "10-K",
  "document_url": "https://www.sec.gov/...",
  "domain": "klaviyo.com",
  "company_name": "Klaviyo, Inc.",
  "analysis": "## Business Overview\n..."
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
