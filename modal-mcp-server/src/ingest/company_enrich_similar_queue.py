"""
Company Enrich Similar Companies - Queue-based Processing

Upload domains to queue table, then trigger batches manually.
Webhook notification when batch completes.
"""

import os
import time
import modal
import requests
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from config import app, image


class ProcessQueueRequest(BaseModel):
    batch_size: int = 300
    webhook_url: Optional[str] = None
    similarity_weight: Optional[float] = 0.0
    country_code: Optional[str] = None


class QueueStatusRequest(BaseModel):
    pass


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("companyenrich-api-key"),
    ],
    timeout=3600,  # 1 hour max
)
def process_queue_batch_worker(
    batch_id: str,
    domains: List[str],
    queue_ids: List[str],
    similarity_weight: float,
    country_code: Optional[str],
    webhook_url: Optional[str],
):
    """
    Background worker that processes a batch from the queue.
    Calls webhook when done.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    companyenrich_key = os.environ["COMPANYENRICH_API_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    processed = 0
    errors = []

    for i, domain in enumerate(domains):
        queue_id = queue_ids[i]
        try:
            _process_single_domain(
                supabase=supabase,
                companyenrich_key=companyenrich_key,
                domain=domain,
                similarity_weight=similarity_weight,
                country_code=country_code,
                batch_id=batch_id,
            )
            processed += 1

            # Mark queue item as done
            supabase.schema("raw").from_("company_enrich_similar_queue").update({
                "status": "done",
                "processed_at": datetime.utcnow().isoformat(),
            }).eq("id", queue_id).execute()

        except Exception as e:
            print(f"Error processing {domain}: {e}")
            errors.append({"domain": domain, "error": str(e)})

            # Mark queue item as error
            supabase.schema("raw").from_("company_enrich_similar_queue").update({
                "status": "error",
                "processed_at": datetime.utcnow().isoformat(),
            }).eq("id", queue_id).execute()

        # Update batch progress
        supabase.schema("raw").from_("company_enrich_similar_batches").update({
            "processed_domains": processed + len(errors)
        }).eq("id", batch_id).execute()

        # Rate limit
        time.sleep(0.5)

    # Mark batch complete
    final_status = "completed" if not errors else "completed_with_errors"
    supabase.schema("raw").from_("company_enrich_similar_batches").update({
        "status": final_status,
        "completed_at": datetime.utcnow().isoformat(),
        "error_message": f"{len(errors)} errors" if errors else None,
    }).eq("id", batch_id).execute()

    # Call webhook if provided
    if webhook_url:
        try:
            webhook_payload = {
                "event": "batch_completed",
                "batch_id": batch_id,
                "status": final_status,
                "total": len(domains),
                "processed": processed,
                "errors": len(errors),
                "error_details": errors[:10] if errors else [],
            }
            requests.post(webhook_url, json=webhook_payload, timeout=10)
        except Exception as e:
            print(f"Webhook failed: {e}")

    return {
        "batch_id": batch_id,
        "status": final_status,
        "processed": processed,
        "errors": len(errors),
    }


def _process_single_domain(
    supabase,
    companyenrich_key: str,
    domain: str,
    similarity_weight: float,
    country_code: str,
    batch_id: str,
) -> dict:
    """Process a single domain: call API, store raw, extract results."""
    api_url = "https://api.companyenrich.com/companies/similar/preview"
    headers = {
        "Authorization": f"Bearer {companyenrich_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "domains": [domain],
        "similarityWeight": similarity_weight,
    }

    if country_code:
        payload["countries"] = [country_code]

    response = requests.post(api_url, json=payload, headers=headers)

    # Store raw response
    raw_insert = (
        supabase.schema("raw")
        .from_("company_enrich_similar_raw")
        .insert({
            "batch_id": batch_id,
            "input_domain": domain,
            "similarity_weight": similarity_weight,
            "country_code": country_code,
            "raw_response": response.json() if response.status_code == 200 else None,
            "status_code": response.status_code,
            "error_message": response.text if response.status_code != 200 else None,
        })
        .execute()
    )
    raw_id = raw_insert.data[0]["id"]

    # Extract similar companies if successful
    extracted_count = 0
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        scores = data.get("metadata", {}).get("scores", {})

        for item in items:
            company_id = item.get("id")
            score = scores.get(str(company_id)) if company_id else None

            supabase.schema("extracted").from_("company_enrich_similar").insert({
                "raw_id": raw_id,
                "batch_id": batch_id,
                "input_domain": domain,
                "company_id": company_id,
                "company_name": item.get("name"),
                "company_domain": item.get("domain"),
                "company_website": item.get("website"),
                "company_industry": item.get("industry"),
                "company_description": item.get("description"),
                "company_keywords": item.get("keywords"),
                "company_logo_url": item.get("logo_url"),
                "similarity_score": score,
            }).execute()
            extracted_count += 1

    return {
        "domain": domain,
        "raw_id": raw_id,
        "status_code": response.status_code,
        "similar_companies_count": extracted_count,
    }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def process_similar_companies_queue(request: ProcessQueueRequest) -> dict:
    """
    Process next N domains from the queue.
    Returns immediately with batch_id.
    Calls webhook_url when done (if provided).
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Get next batch_size pending items from queue
        pending = (
            supabase.schema("raw")
            .from_("company_enrich_similar_queue")
            .select("id, domain")
            .eq("status", "pending")
            .limit(request.batch_size)
            .execute()
        )

        if not pending.data:
            return {
                "success": True,
                "message": "No pending domains in queue",
                "batch_id": None,
                "domains_to_process": 0,
            }

        domains = [r["domain"] for r in pending.data]
        queue_ids = [r["id"] for r in pending.data]

        # Create batch record
        batch_insert = (
            supabase.schema("raw")
            .from_("company_enrich_similar_batches")
            .insert({
                "batch_name": f"queue-batch-{len(domains)}",
                "input_domains": domains,
                "similarity_weight": request.similarity_weight,
                "country_code": request.country_code,
                "status": "processing",
                "total_domains": len(domains),
                "processed_domains": 0,
            })
            .execute()
        )
        batch_id = batch_insert.data[0]["id"]

        # Mark queue items as processing
        for queue_id in queue_ids:
            supabase.schema("raw").from_("company_enrich_similar_queue").update({
                "status": "processing",
                "batch_id": batch_id,
            }).eq("id", queue_id).execute()

        # Spawn background worker
        process_queue_batch_worker.spawn(
            batch_id=batch_id,
            domains=domains,
            queue_ids=queue_ids,
            similarity_weight=request.similarity_weight,
            country_code=request.country_code,
            webhook_url=request.webhook_url,
        )

        return {
            "success": True,
            "batch_id": batch_id,
            "domains_to_process": len(domains),
            "estimated_time_seconds": len(domains) * 0.5,
            "webhook_url": request.webhook_url,
            "message": "Batch started. Webhook will be called when done." if request.webhook_url else "Batch started. Check status with batch_id.",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def get_similar_companies_queue_status(request: QueueStatusRequest) -> dict:
    """
    Get queue status - how many pending, processing, done, error.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Count by status
        all_items = (
            supabase.schema("raw")
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
            "pending": counts["pending"],
            "processing": counts["processing"],
            "done": counts["done"],
            "error": counts["error"],
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
