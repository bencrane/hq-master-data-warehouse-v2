# Company Enrich Similar Companies

Find similar companies using the companyenrich.com API.

## Overview

Given a list of domains, calls the companyenrich.com API to find similar companies. Results are stored in Supabase for querying.

## Architecture

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `find_similar_companies_batch` | Submit batch of domains, returns immediately with batch_id |
| `find_similar_companies_single` | Process single domain synchronously |
| `get_similar_companies_batch_status` | Check batch progress (optional) |
| `process_similar_companies_queue` | Process next N domains from queue table |
| `get_similar_companies_queue_status` | Check queue counts by status |

### Database Tables

**raw.company_enrich_similar_batches** - Batch metadata
- `id`, `batch_name`, `status`, `total_domains`, `processed_domains`, `created_at`, `completed_at`

**raw.company_enrich_similar_raw** - Raw API responses
- `id`, `batch_id`, `input_domain`, `raw_response`, `status_code`, `error_message`

**extracted.company_enrich_similar** - Extracted similar companies
- `id`, `raw_id`, `batch_id`, `input_domain`, `company_id`, `company_name`, `company_domain`, `company_industry`, `company_description`, `similarity_score`

**raw.company_enrich_similar_queue** - Queue for manual batch processing
- `id`, `domain`, `status` (pending/processing/done/error), `batch_id`, `processed_at`

## Usage

### Option 1: Direct Batch (for smaller batches)

```bash
curl -X POST https://bencrane--hq-master-data-ingest-find-similar-companies-batch.modal.run \
  -H "Content-Type: application/json" \
  -d '{
    "domains": ["stripe.com", "shopify.com"],
    "similarity_weight": 0.0,
    "batch_name": "my-batch"
  }'
```

### Option 2: Queue-based (for large batches)

1. Insert domains into queue:
```sql
INSERT INTO raw.company_enrich_similar_queue (domain, status)
SELECT domain, 'pending' FROM your_source_table;
```

2. Trigger processing:
```bash
curl -X POST https://bencrane--hq-master-data-ingest-process-similar-companies-queue.modal.run \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 200}'
```

3. Query results directly from Supabase:
```sql
SELECT * FROM extracted.company_enrich_similar
WHERE input_domain = 'stripe.com';
```

## Rate Limiting

- 0.5 second delay between API requests
- No retry logic - failed domains are skipped and logged
- Recommended batch size: 100-200 domains
- Max timeout: 4 hours per batch

## API Notes

- Uses the `/companies/similar/preview` endpoint (free tier)
- Returns max 25 similar companies per domain
- `similarity_weight` controls industry vs description matching (0.0 = balanced)

## Troubleshooting

### Batch timeout
- Use smaller batches (100-200 domains)
- Check Modal logs for specific errors

### "Response ended prematurely"
- API is flaky under load
- Domain is skipped and logged, processing continues

### Missing results
- Check `raw.company_enrich_similar_raw` for `status_code` != 200
- Re-queue failed domains if needed

## Files

- `src/ingest/company_enrich_similar.py` - Main batch processing
- `src/ingest/company_enrich_similar_queue.py` - Queue-based processing
