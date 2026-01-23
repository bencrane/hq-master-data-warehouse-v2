"""
Lookup Endpoints - query reference tables without storage/AI

- lookup_person_location: Check if location exists in location_lookup (Clay find-people)
- lookup_salesnav_location: Check if location exists in salesnav_location_lookup
- lookup_salesnav_company_location: Check if location exists in salesnav_company_location_lookup
- lookup_job_title: Check if job title exists in job_title_lookup
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class PersonLocationLookupRequest(BaseModel):
    location_name: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_person_location(request: PersonLocationLookupRequest) -> dict:
    """
    Check if location_name exists in reference.location_lookup (Clay find-people).
    Returns match_status=True with city/state/country if found, False otherwise.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("reference")
            .from_("location_lookup")
            .select("city, state, country, has_city, has_state, has_country")
            .eq("location_name", request.location_name)
            .execute()
        )

        if result.data and len(result.data) > 0:
            match = result.data[0]
            return {
                "match_status": True,
                "location_name": request.location_name,
                "city": match.get("city"),
                "state": match.get("state"),
                "country": match.get("country"),
                "has_city": match.get("has_city"),
                "has_state": match.get("has_state"),
                "has_country": match.get("has_country"),
            }
        else:
            return {
                "match_status": False,
                "location_name": request.location_name,
                "city": None,
                "state": None,
                "country": None,
                "has_city": None,
                "has_state": None,
                "has_country": None,
            }

    except Exception as e:
        return {"match_status": False, "error": str(e)}


class LocationLookupRequest(BaseModel):
    location_raw: str


class LocationLookupResponse(BaseModel):
    match_status: bool
    location_raw: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    has_city: Optional[bool] = None
    has_state: Optional[bool] = None
    has_country: Optional[bool] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_salesnav_location(request: LocationLookupRequest) -> dict:
    """
    Check if location_raw exists in reference.salesnav_location_lookup.
    Returns match_status=True with city/state/country if found, False otherwise.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("reference")
            .from_("salesnav_location_lookup")
            .select("city, state, country, has_city, has_state, has_country")
            .eq("location_raw", request.location_raw)
            .execute()
        )

        if result.data and len(result.data) > 0:
            match = result.data[0]
            return {
                "match_status": True,
                "location_raw": request.location_raw,
                "city": match.get("city"),
                "state": match.get("state"),
                "country": match.get("country"),
                "has_city": match.get("has_city"),
                "has_state": match.get("has_state"),
                "has_country": match.get("has_country"),
            }
        else:
            return {
                "match_status": False,
                "location_raw": request.location_raw,
                "city": None,
                "state": None,
                "country": None,
                "has_city": None,
                "has_state": None,
                "has_country": None,
            }

    except Exception as e:
        return {"match_status": False, "error": str(e)}


class CompanyLocationLookupRequest(BaseModel):
    registered_address_raw: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_salesnav_company_location(request: CompanyLocationLookupRequest) -> dict:
    """
    Check if registered_address_raw exists in reference.salesnav_company_location_lookup.
    Returns match_status=True with city/state/country if found, False otherwise.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("reference")
            .from_("salesnav_company_location_lookup")
            .select("city, state, country, has_city, has_state, has_country")
            .eq("registered_address_raw", request.registered_address_raw)
            .execute()
        )

        if result.data and len(result.data) > 0:
            match = result.data[0]
            return {
                "match_status": True,
                "registered_address_raw": request.registered_address_raw,
                "city": match.get("city"),
                "state": match.get("state"),
                "country": match.get("country"),
                "has_city": match.get("has_city"),
                "has_state": match.get("has_state"),
                "has_country": match.get("has_country"),
            }
        else:
            return {
                "match_status": False,
                "registered_address_raw": request.registered_address_raw,
                "city": None,
                "state": None,
                "country": None,
                "has_city": None,
                "has_state": None,
                "has_country": None,
            }

    except Exception as e:
        return {"match_status": False, "error": str(e)}


class JobTitleLookupRequest(BaseModel):
    job_title: str


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def lookup_job_title(request: JobTitleLookupRequest) -> dict:
    """
    Check if job_title exists in reference.job_title_lookup.
    Returns match_status=True with cleaned_job_title/seniority_level/job_function if found.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        result = (
            supabase.schema("reference")
            .from_("job_title_lookup")
            .select("cleaned_job_title, seniority_level, job_function")
            .eq("latest_title", request.job_title)
            .execute()
        )

        if result.data and len(result.data) > 0:
            match = result.data[0]
            return {
                "match_status": True,
                "job_title": request.job_title,
                "cleaned_job_title": match.get("cleaned_job_title"),
                "seniority_level": match.get("seniority_level"),
                "job_function": match.get("job_function"),
            }
        else:
            return {
                "match_status": False,
                "job_title": request.job_title,
                "cleaned_job_title": None,
                "seniority_level": None,
                "job_function": None,
            }

    except Exception as e:
        return {"match_status": False, "error": str(e)}
