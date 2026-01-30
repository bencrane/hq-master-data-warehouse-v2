"""
Email Waterfall Enrichment - Fire-and-forget relay to Clay webhooks
"""

import os
import asyncio
from datetime import datetime
from typing import List

from pydantic import BaseModel
import modal

from config import app, image


class EmailWaterfallRequest(BaseModel):
    records: List[dict]
    clay_webhook_url: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def command_center_email_enrichment(request: EmailWaterfallRequest) -> dict:
    """
    Fire-and-forget endpoint to send records to Clay webhook at rate-limited pace.
    Returns immediately with job_id for tracking.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Create job record
        job_insert = (
            supabase.schema("raw")
            .from_("email_waterfall_jobs")
            .insert({
                "status": "pending",
                "total_records": len(request.records),
                "clay_webhook_url": request.clay_webhook_url,
            })
            .execute()
        )
        job_id = job_insert.data[0]["id"]

        # Spawn background worker
        process_waterfall_batch.spawn(
            job_id=job_id,
            records=request.records,
            clay_webhook_url=request.clay_webhook_url,
        )

        return {
            "success": True,
            "job_id": job_id,
            "total_records": len(request.records),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,
)
async def process_waterfall_batch(job_id: str, records: List[dict], clay_webhook_url: str):
    """
    Background worker that sends records to Clay at 8/sec rate limit.
    """
    import httpx
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    # Update job to processing
    supabase.schema("raw").from_("email_waterfall_jobs").update({
        "status": "processing",
    }).eq("id", job_id).execute()

    sent_count = 0
    failed_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, record in enumerate(records):
            try:
                response = await client.post(clay_webhook_url, json=record)
                if response.status_code == 200:
                    sent_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

            # Rate limit: 8 records/sec = 125ms between requests
            await asyncio.sleep(0.125)

    # Final update
    supabase.schema("raw").from_("email_waterfall_jobs").update({
        "status": "completed",
        "sent_count": sent_count,
        "failed_count": failed_count,
        "completed_at": datetime.utcnow().isoformat(),
    }).eq("id", job_id).execute()


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="GET")
def get_email_job(job_id: str) -> dict:
    """
    Check status of an email waterfall job.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("raw")
            .from_("email_waterfall_jobs")
            .select("*")
            .eq("id", job_id)
            .single()
            .execute()
        )

        if not result.data:
            return {"success": False, "error": "Job not found"}

        job = result.data
        return {
            "success": True,
            "job_id": job["id"],
            "status": job["status"],
            "total_records": job["total_records"],
            "sent_count": job["sent_count"],
            "failed_count": job["failed_count"],
            "created_at": job["created_at"],
            "completed_at": job.get("completed_at"),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

