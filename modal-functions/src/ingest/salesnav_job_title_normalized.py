"""
SalesNav Job Title Normalized Ingest

Stores raw job title -> normalized (SalesNav-friendly) job title mappings.
"""

import os
import modal
from pydantic import BaseModel
from config import app, image


class SalesnavJobTitleNormalizedRequest(BaseModel):
    job_title_raw: str
    normalized_job_title: str | None = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_job_title_normalized(request: SalesnavJobTitleNormalizedRequest) -> dict:
    """
    Upsert a job title normalization mapping.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("reference")
            .from_("salesnav_job_title_normalized")
            .upsert(
                {
                    "job_title_raw": request.job_title_raw,
                    "normalized_job_title": request.normalized_job_title,
                    "updated_at": "now()",
                },
                on_conflict="job_title_raw",
            )
            .execute()
        )

        return {
            "success": True,
            "job_title_raw": request.job_title_raw,
            "normalized_job_title": request.normalized_job_title,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "job_title_raw": request.job_title_raw,
        }
