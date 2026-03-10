# GTM Brief Enrichment Pipeline

Complete documentation of how the Alumni GTM brief enrichment system works end-to-end — from data source to API delivery — including the Trigger.dev orchestration, Parallel AI integration, known problems, and operational runbook.

---

## Overview

The GTM brief enrichment pipeline generates deep-research sales intelligence briefs for alumni leads. For each lead (a person who previously worked at one of our client's customers and now holds a buying role elsewhere), Parallel AI's "pro" processor spends ~10 minutes doing live web research and produces a structured brief: executive summary, opportunity insight, relationship context, talking points, etc.

**The pipeline is NOT real-time.** It's a batch job. Briefs are pre-computed and stored in the database, then served via the `/v1/alumni-gtm/leads` API when a frontend requests them.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. TRIGGER (local machine)                                              │
│                                                                          │
│  scripts/batch-trigger-gtm-briefs.ts                                     │
│    - Fetches unprocessed leads from FastAPI                              │
│    - Calls tasks.batchTrigger() to queue all runs                       │
│    - Exits immediately — does NOT wait for completion                    │
└────────────────────────┬─────────────────────────────────────────────────┘
                         │ HTTP GET
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. FASTAPI (Railway — api.revenueinfra.com)                             │
│                                                                          │
│  GET /parallel-native/gtm-brief/leads                                    │
│    - Reads from core.alumni_gtm_leads view                              │
│    - Filters: has_gtm_brief=false, origin_company_domain, icp_fit       │
│    - Returns leads[] + prompt_template + processor                       │
│                                                                          │
│  POST /parallel-native/gtm-brief/result                                  │
│    - Receives completed brief from Trigger.dev task                      │
│    - Writes raw payload → raw.parallel_person_gtm_briefs                │
│    - Writes extracted output → extracted.parallel_person_gtm_briefs     │
│    - Flips has_gtm_brief=true on core.people_targets                    │
└──────────────┬───────────────────────────────────┬───────────────────────┘
               │                                   ▲
               │ Trigger.dev SDK                   │ HTTP POST (result)
               ▼                                   │
┌──────────────────────────────────────────────────────────────────────────┐
│  3. TRIGGER.DEV (cloud.trigger.dev)                                      │
│                                                                          │
│  Task: gtm-brief-enrichment (trigger/gtm-brief-enrichment.ts)           │
│    - Receives: { lead, prompt_template, processor }                      │
│    - Substitutes {{placeholders}} in prompt with lead data              │
│    - Calls Parallel AI SDK → creates task run                           │
│    - Waits for Parallel AI result (blocks up to 25 min)                 │
│    - POSTs result back to FastAPI                                        │
│                                                                          │
│  Concurrency: 5 simultaneous runs                                        │
│  Max duration: 1500s (25 min)                                            │
│  Retries: 2 attempts                                                     │
└────────────────────────┬─────────────────────────────────────────────────┘
                         │ Parallel AI SDK
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  4. PARALLEL AI (api.parallel.ai)                                        │
│                                                                          │
│  Processor: "pro" (~10 min per lead)                                     │
│    - Deep web research on the person                                     │
│    - Produces unstructured GTM brief                                     │
│    - Returns nested: { output: { content: { ...structured fields } } }  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow (Database)

### Source View: `core.alumni_gtm_leads`

A Postgres view that joins:
- `core.people_targets` — the lead (person + current company)
- `core.person_work_history` — their past jobs
- `core.company_customers` — which past employers are customers of the origin company
- `core.company_targets` — GTM fit scoring for current employer
- `extracted.company_firmographics` — company metadata

**Key columns exposed:**
- `lead_full_name`, `lead_linkedin_url`, `lead_current_job_title`
- `lead_current_company_name`, `lead_current_company_domain`
- `lead_past_company_name`, `lead_past_company_domain`
- `origin_company_name`, `origin_company_domain`
- `icp_fit` — person-level ICP qualification (YES / NO / null)
- `has_gtm_brief` — whether enrichment has been run (boolean)

**WHERE clause (in the view itself):** `ct.gtm_fit = true`

The view does NOT filter by `icp_fit` — that filter is applied at the API layer so we can choose which leads to enrich.

### Prompt Template: `reference.parallel_enrichment_registry`

The prompt template is stored in the database (not in code):
- `slug`: `alumni_person_gtm_brief_unstructured_output`
- `input_template`: JSONB with a `prompt` field containing `{{placeholder}}` variables
- `processor`: `pro`
- `is_active`: true

The Trigger.dev task substitutes view column values into the template placeholders before sending to Parallel AI.

### Variable Mapping (`trigger/config/gtm-brief.ts`)

Maps view columns → prompt template `{{placeholders}}`:

| View Column | Template Variable |
|---|---|
| `origin_company_name` | `{{origin_company_name}}` |
| `origin_company_domain` | `{{origin_company_domain}}` |
| `origin_company_description` | `{{origin_company_description}}` |
| `lead_full_name` | `{{lead_full_name}}` |
| `lead_linkedin_url` | `{{lead_linkedin_url}}` |
| `lead_current_job_title` | `{{lead_current_job_title}}` |
| `lead_current_company_name` | `{{lead_current_company_name}}` |
| `lead_current_company_domain` | `{{lead_current_company_domain}}` |
| `lead_current_company_description` | `{{lead_current_company_description}}` |
| `lead_past_company_name` | `{{lead_past_company_name}}` |
| `lead_past_company_domain` | `{{lead_past_company_domain}}` |
| `lead_past_company_description` | `{{lead_past_company_description}}` |
| `lead_past_company_job_title` | `{{lead_past_company_job_title}}` |

### Storage: Where Results Land

**`raw.parallel_person_gtm_briefs`** — Full Parallel AI response (raw_payload). Always written, even on failure.

**`extracted.parallel_person_gtm_briefs`** — The `output` field extracted from the raw payload. Only written on success. The `output` column is JSONB with this structure:

```json
{
  "content": {
    "memo_title": "...",
    "executive_summary": "...",
    "opportunity_insight": "...",
    "relationship_bridge": "...",
    "current_role_context": "...",
    "prospect_background": "...",
    "talking_points": ["...", "..."],
    "recommended_approach": "...",
    "key_risks_and_considerations": "...",
    "sources": ["...", "..."]
  }
}
```

**`core.people_targets`** — `has_gtm_brief` flipped to `true` on success.

---

## How Briefs Are Served

The `/v1/alumni-gtm/leads` endpoint (`hq-api/routers/alumni_gtm.py`) batch-fetches briefs:

```python
brief_rows = await conn.fetch(
    "SELECT person_linkedin_url, output FROM extracted.parallel_person_gtm_briefs "
    "WHERE person_linkedin_url = ANY($1::text[]) AND origin_company_domain = $2",
    linkedin_urls, origin_domain
)
for br in brief_rows:
    output = br["output"]
    if isinstance(output, str):
        output = json.loads(output)
    gtm_brief_map[br["person_linkedin_url"]] = output.get("content") if isinstance(output, dict) else output
```

**Critical:** The `.get("content")` extraction is essential. The raw `output` column contains verbose Parallel AI reasoning text at the top level. The actual structured brief is nested under `output.content`. Without this extraction, the API returns 15KB of raw reasoning per lead instead of the clean structured brief.

---

## File Reference

| File | Role |
|---|---|
| `scripts/batch-trigger-gtm-briefs.ts` | CLI script to batch-trigger enrichment runs |
| `scripts/trigger_one_lead.ts` | One-off script to trigger a single lead (testing) |
| `trigger/gtm-brief-enrichment.ts` | The Trigger.dev task (runs in cloud) |
| `trigger/config/gtm-brief.ts` | Config: processor, maxDuration, variable mapping |
| `trigger.config.ts` | Trigger.dev project config (project ID, retries) |
| `hq-api/routers/parallel_native.py` | FastAPI endpoints: fetch leads, store results |
| `hq-api/routers/alumni_gtm.py` | FastAPI endpoint: serve leads + briefs to frontend |

---

## Operational Runbook

### Triggering a Batch

```bash
# All icp_fit=YES leads for a domain (recommended)
TRIGGER_SECRET_KEY="tr_prod_..." HQ_API_URL="https://api.revenueinfra.com" \
  npx tsx scripts/batch-trigger-gtm-briefs.ts <domain> <limit> YES

# Example: 133 SecurityPal leads
TRIGGER_SECRET_KEY="tr_prod_..." HQ_API_URL="https://api.revenueinfra.com" \
  npx tsx scripts/batch-trigger-gtm-briefs.ts securitypalhq.com 133 YES

# All leads regardless of ICP fit (omit 4th arg)
TRIGGER_SECRET_KEY="tr_prod_..." HQ_API_URL="https://api.revenueinfra.com" \
  npx tsx scripts/batch-trigger-gtm-briefs.ts nostra.ai 100
```

**Args:** `<origin_domain> <limit> [icp_fit]`

### Triggering a Single Lead (Testing)

```bash
TRIGGER_SECRET_KEY="tr_prod_..." HQ_API_URL="https://api.revenueinfra.com" \
  npx tsx scripts/trigger_one_lead.ts
```

Note: `trigger_one_lead.ts` currently has the secret key hardcoded and is pinned to `securitypalhq.com`. It was a quick test script.

### Monitoring

Trigger.dev dashboard: https://cloud.trigger.dev/orgs/substrate-9087/projects/hq-data-warehouse-TX-p

Shows: running count, queued count, completed, failed, avg duration per run.

### Deploying Task Code Changes

If you modify `trigger/gtm-brief-enrichment.ts` or `trigger/config/gtm-brief.ts`:

```bash
doppler run -- npx trigger.dev@latest deploy
```

This deploys the task code to Trigger.dev cloud. It does NOT trigger any runs — it just updates the task definition.

### Checking How Many Leads Need Enrichment

```bash
curl -s "https://api.revenueinfra.com/parallel-native/gtm-brief/leads?origin_company_domain=DOMAIN&limit=1000" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Total: {d[\"count\"]}')"

# With icp_fit breakdown
curl -s "https://api.revenueinfra.com/parallel-native/gtm-brief/leads?origin_company_domain=DOMAIN&limit=1000" \
  | python3 -c "
import sys,json
from collections import Counter
d=json.load(sys.stdin)
counts = Counter(l.get('icp_fit') for l in d['leads'])
print(f'Total unprocessed: {d[\"count\"]}')
for k,v in sorted(counts.items(), key=lambda x: -x[1]):
    print(f'  icp_fit={k}: {v}')
"
```

---

## Known Problems and Sharp Edges

### 1. Environment Variables Are a Mess

**Problem:** `TRIGGER_SECRET_KEY` and `HQ_API_URL` are not in Doppler. The batch trigger script requires them but `doppler run --` doesn't inject them. You have to pass them inline:

```bash
TRIGGER_SECRET_KEY="tr_prod_..." HQ_API_URL="https://api.revenueinfra.com" npx tsx scripts/...
```

**Why it matters:** Every time you (or someone else) needs to trigger a batch, they need to know the secret key. It's not documented anywhere centrally. The `trigger_one_lead.ts` script has it hardcoded which is bad practice.

**Fix:** Add `TRIGGER_SECRET_KEY` and `HQ_API_URL` to Doppler so `doppler run --` works as expected. Then remove the hardcoded key from `trigger_one_lead.ts`.

### 2. Parallel AI Pro Processor Is Slow (~10 min/lead)

**Problem:** At concurrency 5 and ~10 min per lead, 133 leads takes ~4.5 hours (not ~2.25 hours as naively estimated). The Trigger.dev dashboard showed avg duration of ~10m per run.

**Why it matters:** Batch enrichment is an hours-long operation. You can't quickly enrich a new client's leads.

**Options:**
- Increase concurrency limit (currently 5 in `trigger/gtm-brief-enrichment.ts` queue config). Risk: Parallel AI rate limits.
- Use `lite` or `base` processor for lower-priority leads. Risk: Lower quality briefs.
- Pre-filter aggressively with `icp_fit=YES` to reduce volume (what we do now).

### 3. No Progress Tracking or Webhook on Batch Completion

**Problem:** After `batchTrigger()` fires, the script exits. There's no callback, no webhook, no notification when the batch finishes. You have to manually check the Trigger.dev dashboard.

**Why it matters:** For a 4+ hour batch, you're blind. No way to know when it's done without checking manually.

**Fix options:**
- Add a Trigger.dev scheduled task that polls for batch completion
- Use Trigger.dev's `batchTriggerAndWait()` in a long-running task (but the script would need to stay alive)
- Set up a Trigger.dev webhook to POST to Slack or email on batch completion
- The `POST /parallel-native/gtm-brief/result` endpoint could track count-remaining and fire a notification

### 4. `output.content` Nesting Is Fragile

**Problem:** Parallel AI returns `{ output: { content: { ...actual brief } } }`. The Trigger.dev task stores `runResult.output` (or `runResult` itself) into the `output` column. The alumni_gtm.py endpoint then does `output.get("content")` to extract the actual brief.

This nesting depends on:
- Parallel AI's response structure staying consistent
- The Trigger.dev task storing the right level of the response
- The alumni_gtm.py endpoint knowing to unwrap `.content`

If any of these change, briefs either break (null) or bloat (raw reasoning text returns to the frontend — which already happened once).

**Why it matters:** We already had a bug where the raw `output` was being returned instead of `output.content`, causing the frontend to display verbose AI reasoning text instead of structured briefs.

**Fix:** The extraction should happen at write-time (in `POST /parallel-native/gtm-brief/result`), not at read-time. Store only the clean `content` object in `extracted.parallel_person_gtm_briefs.output` so every consumer gets clean data without needing to know the nesting structure.

### 5. No Idempotency Guard on Re-Enrichment

**Problem:** If you run the batch trigger twice for the same domain, the second run will skip already-enriched leads (because `has_gtm_brief=true` filters them out of the view). BUT if a run fails and doesn't flip `has_gtm_brief`, it can be re-enriched on the next batch — creating duplicate rows in `raw.parallel_person_gtm_briefs` and `extracted.parallel_person_gtm_briefs`.

**Why it matters:** You could end up with multiple extracted briefs for the same person, and the alumni_gtm.py endpoint would pick whichever row the query returns first (nondeterministic).

**Fix:** Add a unique constraint on `(person_linkedin_url, origin_company_domain)` in `extracted.parallel_person_gtm_briefs` with `ON CONFLICT DO UPDATE`, or add `ORDER BY created_at DESC LIMIT 1` to the brief lookup query.

### 6. No Auth on the Pipeline Endpoints

**Problem:** `GET /parallel-native/gtm-brief/leads` and `POST /parallel-native/gtm-brief/result` have no authentication. Anyone who knows the URL can fetch all unprocessed leads or POST fake results.

**Why it matters:** The result endpoint flips `has_gtm_brief=true` and writes to the database. A malicious POST could corrupt data.

**Fix:** Add API key auth (even a simple bearer token check) to both endpoints. The Trigger.dev task already has `HQ_API_URL` as an env var — add an `HQ_API_KEY` and send it as a header.

### 7. `batchTrigger` Returns `undefined` for Batch ID

**Problem:** The script logs `Batch triggered! ID: undefined`. The `tasks.batchTrigger()` return value's `.id` field is undefined, suggesting the SDK version or response shape doesn't include a batch ID.

**Why it matters:** Can't programmatically track the batch. Makes monitoring harder.

**Fix:** Check Trigger.dev SDK docs for the correct return shape. May need to upgrade the SDK or access the batch ID differently (e.g., `batch.batchId` or `batch.runs`).

### 8. Concurrency Limit Is Set in Task Code, Not Configurable at Trigger Time

**Problem:** The concurrency limit of 5 is hardcoded in `trigger/gtm-brief-enrichment.ts`:

```ts
queue: { concurrencyLimit: 5 }
```

Changing it requires a code change + deploy (`doppler run -- npx trigger.dev@latest deploy`).

**Why it matters:** Can't dynamically adjust concurrency based on load, budget, or urgency.

**Mitigation:** This is a Trigger.dev limitation. The concurrency is per-queue, set at task definition time. To work around it, you'd need multiple task definitions with different concurrency limits, or use the Trigger.dev dashboard to override (if supported).

---

## Cost Awareness

Parallel AI "pro" processor is the most expensive standard tier. Each run costs credits.

| Metric | Value |
|---|---|
| Processor | pro |
| Avg duration | ~10 min |
| Cost per lead | Varies (check Parallel billing) |
| SecurityPal batch (icp_fit=YES) | 133 leads |
| SecurityPal batch (all gtm_fit=true) | 676 leads |
| Credits saved by icp_fit filter | ~80% (543 NO leads skipped) |

**Always filter by `icp_fit=YES`** unless there's a specific reason to enrich NO leads. The icp_fit filter was added specifically to avoid burning credits on low-value leads.

The "ultra" processor exists but is more expensive and slower. Pro output quality was assessed as strong — real research, actionable briefs, structured fields — so ultra is not justified for most use cases.

---

## Timeline of Key Decisions

1. **View created without icp_fit column** → Could not filter leads at the API layer → Fixed by `DROP VIEW` + `CREATE VIEW` adding `icp_fit`
2. **View had `WHERE icp_fit = 'YES'`** → Excluded leads from view entirely, no way to see NO leads → Fixed by removing from WHERE, filtering at API layer instead
3. **`output` returned raw to frontend** → 15KB of Parallel reasoning per lead → Fixed with `.get("content")` extraction in alumni_gtm.py
4. **`CREATE OR REPLACE VIEW` attempted to add column** → Postgres error: cannot rename columns → Fixed with `DROP VIEW` + `CREATE VIEW`
5. **PAT token used for triggering** → Auth rejected (PATs are CLI-only) → Fixed by using project secret key (`tr_prod_*`)
6. **`doppler run --` didn't have trigger env vars** → Script failed → Worked around with inline env vars

---

## Future Improvements (Prioritized)

1. **Add TRIGGER_SECRET_KEY and HQ_API_URL to Doppler** — Immediate, removes friction
2. **Add auth to pipeline endpoints** — Security, prevents data corruption
3. **Move `output.content` extraction to write-time** — Prevents future frontend bugs
4. **Add unique constraint on extracted briefs** — Prevents duplicates
5. **Add batch completion notification** — Slack webhook or similar
6. **Make concurrency configurable** — Possibly via Trigger.dev dashboard or env var
7. **Consider `batchTriggerAndWait` pattern** — For smaller batches where you want to know when it's done
