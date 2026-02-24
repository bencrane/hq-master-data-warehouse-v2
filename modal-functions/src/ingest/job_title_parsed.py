"""
Job Title Parsed Ingest

Stores raw job title -> cleaned job title mappings in the canonical reference table.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class JobTitleParsedRequest(BaseModel):
    raw_job_title: str
    cleaned_job_title: str
    seniority: Optional[str] = None
    job_function: Optional[str] = None
    source: str = "case-study-champions"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_job_title_parsed(request: JobTitleParsedRequest) -> dict:
    """
    Upsert a job title mapping to reference.job_title_parsed.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        data = {
            "raw_job_title": request.raw_job_title,
            "cleaned_job_title": request.cleaned_job_title,
            "source": request.source,
        }

        if request.seniority:
            data["seniority"] = request.seniority
        if request.job_function:
            data["job_function"] = request.job_function

        # Check if this raw_job_title + source combo exists
        existing = (
            supabase.schema("reference")
            .table("job_title_parsed")
            .select("id")
            .eq("raw_job_title", request.raw_job_title)
            .eq("source", request.source)
            .limit(1)
            .execute()
        )

        if existing.data:
            # Update existing
            result = (
                supabase.schema("reference")
                .table("job_title_parsed")
                .update(data)
                .eq("raw_job_title", request.raw_job_title)
                .eq("source", request.source)
                .execute()
            )
        else:
            # Insert new
            result = (
                supabase.schema("reference")
                .table("job_title_parsed")
                .insert(data)
                .execute()
            )

        return {
            "success": True,
            "raw_job_title": request.raw_job_title,
            "cleaned_job_title": request.cleaned_job_title,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "raw_job_title": request.raw_job_title,
        }
