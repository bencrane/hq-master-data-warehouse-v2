# Workflows - Modal Data Pipelines

Documentation for Modal serverless functions that power data ingestion and enrichment.

---

## Overview

Modal functions receive webhooks from Clay and other sources, then write data through the schema layers:

```
Clay Webhook -> Modal Function -> raw -> extracted -> (optional) core
```

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [Development Guide](./development-guide.md) | How to create and deploy Modal functions |
| [Endpoint Checklist](./endpoint-checklist.md) | Pre-deployment verification |
| [Workflow Creation](./workflow-creation.md) | Step-by-step workflow creation |

---

## Workflow Catalog

Individual workflow documentation lives in [`catalog/`](./catalog/).

| Workflow | Type | Coalesces to Core |
|----------|------|-------------------|
| [Company Discovery](./catalog/upsert-core-company-full.md) | Company | Yes |
| [Case Study Buyers](./catalog/ingest-case-study-buyers.md) | Company | Yes |
| [VC Portfolio](./catalog/ingest-cb-vc-portfolio.md) | Company | No |
| [Job Change Signal](./catalog/signal-job-change.md) | Person | Partial |
| [Promotion Signal](./catalog/signal-promotion.md) | Person | Partial |
| [Person Job Titles](./catalog/backfill-person-job-titles.md) | Person | Yes |
| ... | ... | ... |

---

## Code Location

Modal function source code: `/modal-functions/src/`

```
modal-functions/src/
├── app.py              # Modal app configuration
├── config.py           # Configuration
├── ingest/             # Ingestion endpoints (~53 functions)
├── extraction/         # Data extraction
├── cleanup/            # Data cleanup
└── icp/                # ICP generation
```

---

## Deployment

```bash
cd modal-functions
modal deploy src/app.py
```

---

## Known Issues

- **`reference.enrichment_workflow_registry` table does NOT exist** — needs to be created
- ~87 Modal ingest functions exist but none are registered in the database
- See [workflow-registry-audit.md](/docs/workbench/active/workflow-registry-audit.md) for details
