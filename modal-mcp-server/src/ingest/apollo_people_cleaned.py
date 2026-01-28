"""
Apollo People Cleaned - Receives cleaned person data from Clay
"""

import os
import modal
from pydantic import BaseModel, Field
from typing import Optional

from config import app, image


class ApolloPeopleCleanedRequest(BaseModel):
    linkedin_url: Optional[str] = None
    apollo_person_url: Optional[str] = None
    photo_url: Optional[str] = None
    full_name: Optional[str] = None
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    cleaned_job_title: Optional[str] = Field(None, alias="cleaned-job-title")
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    person_location: Optional[str] = None

    class Config:
        populate_by_name = True


def normalize_null_string(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' or empty to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_apollo_people_cleaned(request: ApolloPeopleCleanedRequest) -> dict:
    """
    Ingest cleaned Apollo person data from Clay.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        data = {
            "linkedin_url": normalize_null_string(request.linkedin_url),
            "apollo_person_url": normalize_null_string(request.apollo_person_url),
            "photo_url": normalize_null_string(request.photo_url),
            "full_name": normalize_null_string(request.full_name),
            "job_title": normalize_null_string(request.job_title),
            "company_name": normalize_null_string(request.company_name),
            "person_location": normalize_null_string(request.person_location),
            "cleaned_first_name": normalize_null_string(request.cleaned_first_name),
            "cleaned_last_name": normalize_null_string(request.cleaned_last_name),
            "cleaned_full_name": normalize_null_string(request.cleaned_full_name),
            "cleaned_job_title": normalize_null_string(request.cleaned_job_title),
        }

        result = (
            supabase.schema("extracted")
            .from_("apollo_people_cleaned")
            .insert(data)
            .execute()
        )

        record_id = result.data[0]["id"] if result.data else None

        return {
            "success": True,
            "id": record_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
