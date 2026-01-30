"""
Backfill cleaned_name column in core.companies from extracted.cleaned_company_names
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class BackfillRequest(BaseModel):
    batch_size: int = 5000
    max_batches: Optional[int] = None  # None = run until done


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=600,  # 10 minutes
)
@modal.fastapi_endpoint(method="POST")
def backfill_cleaned_company_name(request: BackfillRequest) -> dict:
    """
    Backfill cleaned_name in core.companies from extracted.cleaned_company_names.

    Processes in batches to avoid timeouts.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    total_updated = 0
    batches_processed = 0

    try:
        while True:
            # Check if we've hit max batches
            if request.max_batches and batches_processed >= request.max_batches:
                break

            # Get batch of companies without cleaned_name that have a match
            result = supabase.rpc(
                'backfill_cleaned_company_names_batch',
                {'batch_size': request.batch_size}
            ).execute()

            updated = result.data if result.data else 0

            if updated == 0:
                break

            total_updated += updated
            batches_processed += 1

        return {
            "success": True,
            "total_updated": total_updated,
            "batches_processed": batches_processed,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_updated": total_updated,
            "batches_processed": batches_processed,
        }
