# analyze_sec_8k_executive

> **Last Updated:** 2026-02-03

## Purpose

Analyzes an SEC 8-K filing about executive changes using Gemini.

## Use Case

You have an 8-K document URL with item code 5.02 (executive departures/appointments). Send it to Gemini for analysis to get:
- Who left (name, title, effective date)
- Who joined (name, title, background)
- Why (reason given)
- Sales implication

## Endpoints

**Modal (direct):**
```
POST https://bencrane--hq-master-data-ingest-analyze-sec-8k-executive.modal.run
```

**HQ API (wrapper):** Not yet implemented

## Expected Payload

```json
{
  "document_url": "https://www.sec.gov/Archives/edgar/data/1835830/000183583025000116/kvyo-20251208.htm",
  "domain": "klaviyo.com",
  "company_name": "Klaviyo, Inc."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| document_url | string | Yes | SEC 8-K filing document URL |
| domain | string | No | Company domain for context |
| company_name | string | No | Company name for context |

## Response

```json
{
  "success": true,
  "filing_type": "8-K-executive",
  "document_url": "https://www.sec.gov/...",
  "domain": "klaviyo.com",
  "company_name": "Klaviyo, Inc.",
  "analysis": "## Who left?\n..."
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
