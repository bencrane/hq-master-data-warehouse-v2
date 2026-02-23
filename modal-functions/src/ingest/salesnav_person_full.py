"""
SalesNav Person Full Ingestion Endpoint

Ingests person data from SalesNav scrapes including work history.
Populates:
- extracted.salesnav_scrapes_person (person data)
- core.person_work_history (all jobs)
- core.person_past_employer (past jobs for alumni lookup)
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List
from config import app, image


class WorkHistoryEntry(BaseModel):
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False


class SalesNavPersonFullRequest(BaseModel):
    # Person info
    linkedin_url: str  # Required - primary key
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    profile_headline: Optional[str] = None
    location: Optional[str] = None

    # Current job (convenience - also in work_history)
    current_company_name: Optional[str] = None
    current_company_domain: Optional[str] = None
    current_job_title: Optional[str] = None

    # Work history
    work_history: Optional[List[WorkHistoryEntry]] = None

    # Metadata
    source: str = "salesnav"
    scrape_settings_id: Optional[str] = None


def normalize_null(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_person_full(request: SalesNavPersonFullRequest) -> dict:
    """
    Ingest SalesNav person with full work history.

    1. Upserts to extracted.salesnav_scrapes_person
    2. Upserts work history to core.person_work_history
    3. Inserts past employers to core.person_past_employer (for alumni lookup)
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        linkedin_url = normalize_null(request.linkedin_url)
        if not linkedin_url:
            return {"success": False, "error": "linkedin_url is required"}

        # 1. Upsert person to extracted.salesnav_scrapes_person
        person_data = {
            "linkedin_url": linkedin_url,
            "first_name": normalize_null(request.first_name),
            "last_name": normalize_null(request.last_name),
            "cleaned_full_name": normalize_null(request.full_name),
            "email": normalize_null(request.email),
            "phone_number": normalize_null(request.phone_number),
            "profile_headline": normalize_null(request.profile_headline),
            "location_raw": normalize_null(request.location),
            "company_name": normalize_null(request.current_company_name),
            "domain": normalize_null(request.current_company_domain),
            "job_title": normalize_null(request.current_job_title),
        }

        person_result = (
            supabase.schema("extracted")
            .from_("salesnav_scrapes_person")
            .upsert(person_data, on_conflict="linkedin_url")
            .execute()
        )
        person_id = person_result.data[0]["id"] if person_result.data else None

        # 2. Process work history
        work_history_count = 0
        past_employer_count = 0

        if request.work_history:
            for idx, job in enumerate(request.work_history):
                company_name = normalize_null(job.company_name)
                company_domain = normalize_null(job.company_domain)

                if not company_name and not company_domain:
                    continue

                # Upsert to core.person_work_history
                work_data = {
                    "linkedin_url": linkedin_url,
                    "company_name": company_name,
                    "company_domain": company_domain,
                    "company_linkedin_url": normalize_null(job.company_linkedin_url),
                    "title": normalize_null(job.title),
                    "start_date": normalize_null(job.start_date),
                    "end_date": normalize_null(job.end_date),
                    "is_current": job.is_current,
                    "experience_order": idx,
                    "source_id": request.scrape_settings_id,
                }

                # Use upsert with composite key
                supabase.schema("core").from_("person_work_history").upsert(
                    work_data,
                    on_conflict="linkedin_url,company_domain,title"
                ).execute()
                work_history_count += 1

                # 3. If past job, also insert to person_past_employer
                if not job.is_current and company_domain:
                    past_employer_data = {
                        "linkedin_url": linkedin_url,
                        "past_company_name": company_name,
                        "past_company_domain": company_domain,
                        "source": request.source,
                        "scrape_settings_id": request.scrape_settings_id,
                    }

                    # Upsert to avoid duplicates
                    supabase.schema("core").from_("person_past_employer").upsert(
                        past_employer_data,
                        on_conflict="linkedin_url,past_company_domain"
                    ).execute()
                    past_employer_count += 1

        return {
            "success": True,
            "linkedin_url": linkedin_url,
            "person_id": person_id,
            "work_history_count": work_history_count,
            "past_employer_count": past_employer_count,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
