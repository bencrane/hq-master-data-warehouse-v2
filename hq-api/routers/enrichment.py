"""
Enrichment API endpoints.

Wraps Modal functions for data enrichment operations.
"""

import os
import httpx
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from db import core, extracted, raw

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])

MODAL_PROCESS_QUEUE_URL = os.getenv(
    "MODAL_PROCESS_QUEUE_URL",
    "https://bencrane--hq-master-data-ingest-process-similar-companies-queue.modal.run"
)


class BatchSubmitRequest(BaseModel):
    domains: List[str]
    batch_size: int = 200


@router.get("/similar-companies/pending")
async def get_pending_similar_companies(
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
):
    """
    Get domains that have customer data but no similar companies data.
    These are candidates for enrichment.
    """
    # Get customer domains
    customers_result = (
        core()
        .from_("company_customers")
        .select("customer_domain")
        .not_.is_("customer_domain", "null")
        .execute()
    )

    if not customers_result.data:
        return {
            "success": True,
            "pending_domains": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    # Get unique customer domains
    customer_domains = list(set(
        row["customer_domain"] for row in customers_result.data
        if row.get("customer_domain") and row["customer_domain"].strip()
    ))

    # Get domains that already have similar companies data
    existing_result = (
        extracted()
        .from_("company_enrich_similar")
        .select("input_domain")
        .execute()
    )

    existing_domains = set(
        row["input_domain"] for row in existing_result.data
        if row.get("input_domain")
    )

    # Find domains without similar companies
    pending_domains = [d for d in customer_domains if d not in existing_domains]
    pending_domains.sort()

    # Apply pagination
    total = len(pending_domains)
    paginated = pending_domains[offset:offset + limit]

    return {
        "success": True,
        "pending_domains": paginated,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
    }


@router.post("/similar-companies/batch")
async def submit_similar_companies_batch(request: BatchSubmitRequest):
    """
    Submit domains for similar companies enrichment.

    Inserts domains into the queue table and triggers processing.
    Returns immediately with batch info - processing happens async.
    """
    if not request.domains:
        return {
            "success": False,
            "error": "No domains provided",
        }

    # Dedupe and clean domains
    domains = list(set(d.lower().strip() for d in request.domains if d and d.strip()))

    if not domains:
        return {
            "success": False,
            "error": "No valid domains after cleaning",
        }

    try:
        # Insert domains into queue table
        queue_records = [
            {"domain": domain, "status": "pending"}
            for domain in domains
        ]

        # Insert in chunks to avoid payload size limits
        chunk_size = 500
        inserted_count = 0
        for i in range(0, len(queue_records), chunk_size):
            chunk = queue_records[i:i + chunk_size]
            raw().from_("company_enrich_similar_queue").insert(chunk).execute()
            inserted_count += len(chunk)

        # Trigger Modal to process the queue
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                MODAL_PROCESS_QUEUE_URL,
                json={
                    "batch_size": min(request.batch_size, len(domains)),
                    "similarity_weight": 0.0,
                },
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to trigger processing: {response.status_code}",
                    "queued_domains": inserted_count,
                    "detail": response.text[:500],
                }

            modal_result = response.json()

        return {
            "success": True,
            "queued_domains": inserted_count,
            "batch_id": modal_result.get("batch_id"),
            "domains_processing": modal_result.get("domains_to_process", 0),
            "estimated_time_seconds": modal_result.get("estimated_time_seconds"),
            "message": "Batch submitted. Poll /batch/{batch_id}/status for progress.",
        }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Timeout triggering batch processing",
            "queued_domains": inserted_count if 'inserted_count' in locals() else 0,
            "suggestion": "Domains are queued. Try triggering processing again.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/similar-companies/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """
    Get status of a similar companies batch.
    """
    try:
        batch_result = (
            raw()
            .from_("company_enrich_similar_batches")
            .select("*")
            .eq("id", batch_id)
            .limit(1)
            .execute()
        )

        if not batch_result.data:
            raise HTTPException(status_code=404, detail="Batch not found")

        batch = batch_result.data[0]

        response = {
            "success": True,
            "batch_id": batch["id"],
            "status": batch["status"],
            "total_domains": batch["total_domains"],
            "processed_domains": batch["processed_domains"],
            "progress_percent": round(
                (batch["processed_domains"] / batch["total_domains"]) * 100
                if batch["total_domains"] > 0 else 0,
                1
            ),
            "created_at": batch["created_at"],
            "completed_at": batch["completed_at"],
            "error_message": batch.get("error_message"),
        }

        # If completed, get result counts
        if batch["status"] in ("completed", "completed_with_errors"):
            results = (
                extracted()
                .from_("company_enrich_similar")
                .select("input_domain", count="exact", head=True)
                .eq("batch_id", batch_id)
                .execute()
            )
            response["similar_companies_found"] = results.count or 0

        return response

    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/similar-companies/queue/status")
async def get_queue_status():
    """
    Get overall queue status - pending, processing, done, error counts.
    """
    try:
        all_items = (
            raw()
            .from_("company_enrich_similar_queue")
            .select("status")
            .execute()
        )

        counts = {"pending": 0, "processing": 0, "done": 0, "error": 0}
        for item in all_items.data:
            status = item.get("status", "pending")
            counts[status] = counts.get(status, 0) + 1

        return {
            "success": True,
            "total": len(all_items.data),
            **counts,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
