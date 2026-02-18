"""
SalesNav Clay Basic Ingestion Endpoint

Same as salesnav_clay_ingest but WITHOUT ex_company_domain.
For SalesNav data where we only have current employer, no alumni context.

Data flow:
1. Raw: Store full Clay payload to raw.salesnav_scrapes_person_payloads
2. Extracted:
   - extracted.salesnav_scrapes_person
   - extracted.salesnav_scrapes_companies
3. Core:
   - core.companies: Upsert current employer
   - core.people: Upsert person (linkedin_url_type = 'salesnav')
   - core.company_linkedin_urls: Store company LinkedIn URL
   - core.person_work_history: Current job record
   - core.person_job_start_dates: Job start date (if present)

Note: SalesNav LinkedIn URLs are hashed/sales-specific, NOT real profile URLs.
We store them with linkedin_url_type = 'salesnav'.
"""

import os
import modal
from pydantic import BaseModel

from config import app, image


class SalesNavClayBasicRequest(BaseModel):
    """Request model for Clay SalesNav webhook (no ex_company_domain)."""
    raw_payload: dict


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_clay_basic(request: SalesNavClayBasicRequest) -> dict:
    """
    Ingest SalesNav person data from Clay webhook.
    No past employer tracking - just current employer data.
    """
    from supabase import create_client
    from extraction.salesnav_clay import (
        extract_salesnav_clay_person,
        extract_salesnav_clay_company,
        normalize_null_string,
        extract_domain_from_url,
        parse_job_start_date,
    )

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    result = {
        "success": False,
        "raw_id": None,
        "extracted_person_id": None,
        "extracted_company_id": None,
        "core_company_id": None,
        "core_person_id": None,
        "work_history_id": None,
        "job_start_date_id": None,
    }

    try:
        payload = request.raw_payload

        # Extract key fields
        person_linkedin_url = normalize_null_string(
            payload.get("LinkedIn URL (user profile)")
        )
        linkedin_urn = normalize_null_string(payload.get("LinkedIn user profile URN"))
        company_website = normalize_null_string(payload.get("Company website"))
        current_company_domain = extract_domain_from_url(company_website)
        company_name = normalize_null_string(payload.get("Company"))
        company_linkedin_url = normalize_null_string(payload.get("LinkedIn URL (company)"))
        first_name = normalize_null_string(payload.get("First name"))
        last_name = normalize_null_string(payload.get("Last name"))
        job_title = normalize_null_string(payload.get("Job title"))
        job_started_on = normalize_null_string(payload.get("Job started on"))

        # Build full name
        full_name = None
        if first_name and last_name:
            full_name = f"{first_name} {last_name}"
        elif first_name:
            full_name = first_name
        elif last_name:
            full_name = last_name

        # Parse job start date (MM-YYYY -> date)
        job_start_date = parse_job_start_date(job_started_on)

        # =========================================================================
        # 1. RAW: Store full payload
        # =========================================================================
        raw_insert = (
            supabase.schema("raw")
            .from_("salesnav_scrapes_person_payloads")
            .insert({
                "person_linkedin_sales_nav_url": person_linkedin_url,
                "linkedin_user_profile_urn": linkedin_urn,
                "domain": current_company_domain,
                "workflow_slug": "salesnav-clay-basic",
                "raw_payload": payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]
        result["raw_id"] = raw_id

        # =========================================================================
        # 2. EXTRACTED: Person and Company
        # =========================================================================
        extracted_person = extract_salesnav_clay_person(
            supabase=supabase,
            raw_payload_id=raw_id,
            payload=payload,
        )
        result["extracted_person_id"] = extracted_person["id"] if extracted_person else None

        extracted_company = extract_salesnav_clay_company(
            supabase=supabase,
            payload=payload,
        )
        result["extracted_company_id"] = extracted_company["id"] if extracted_company else None

        # =========================================================================
        # 3. CORE: Companies
        # =========================================================================
        core_company_id = None
        if current_company_domain:
            existing = (
                supabase.schema("core")
                .from_("companies")
                .select("id")
                .eq("domain", current_company_domain)
                .execute()
            )
            if existing.data:
                core_company_id = existing.data[0]["id"]
            else:
                inserted = (
                    supabase.schema("core")
                    .from_("companies")
                    .insert({
                        "domain": current_company_domain,
                        "name": company_name,
                        "linkedin_url": company_linkedin_url,
                    })
                    .execute()
                )
                core_company_id = inserted.data[0]["id"] if inserted.data else None
            result["core_company_id"] = core_company_id

        # =========================================================================
        # 4. CORE: Company LinkedIn URLs
        # =========================================================================
        if current_company_domain and company_linkedin_url:
            try:
                supabase.schema("core").from_("company_linkedin_urls").upsert(
                    {
                        "domain": current_company_domain,
                        "linkedin_url": company_linkedin_url,
                        "source": "salesnav-clay-basic",
                    },
                    on_conflict="domain"
                ).execute()
            except Exception:
                pass  # Table may not be exposed in PostgREST

        # =========================================================================
        # 5. CORE: People
        # =========================================================================
        core_person_id = None
        if person_linkedin_url:
            existing = (
                supabase.schema("core")
                .from_("people")
                .select("id")
                .eq("linkedin_url", person_linkedin_url)
                .execute()
            )
            if existing.data:
                core_person_id = existing.data[0]["id"]
            else:
                inserted = (
                    supabase.schema("core")
                    .from_("people")
                    .insert({
                        "linkedin_url": person_linkedin_url,
                        "linkedin_url_type": "salesnav",
                        "linkedin_user_profile_urn": linkedin_urn,
                        "full_name": full_name,
                        "core_company_id": core_company_id,
                    })
                    .execute()
                )
                core_person_id = inserted.data[0]["id"] if inserted.data else None
            result["core_person_id"] = core_person_id

        # =========================================================================
        # 6. CORE: Person Work History (current job)
        # =========================================================================
        if person_linkedin_url and current_company_domain:
            work_history_insert = (
                supabase.schema("core")
                .from_("person_work_history")
                .insert({
                    "linkedin_url": person_linkedin_url,
                    "linkedin_url_type": "salesnav",
                    "company_domain": current_company_domain,
                    "company_name": company_name,
                    "company_linkedin_url": company_linkedin_url,
                    "title": job_title,
                    "start_date": job_start_date.isoformat() if job_start_date else None,
                    "is_current": True,
                })
                .execute()
            )
            result["work_history_id"] = work_history_insert.data[0]["id"] if work_history_insert.data else None

        # =========================================================================
        # 7. CORE: Person Job Start Dates
        # =========================================================================
        if person_linkedin_url and job_start_date:
            supabase.schema("core").from_("person_job_start_dates").upsert(
                {
                    "person_linkedin_url": person_linkedin_url,
                    "linkedin_url_type": "salesnav",
                    "job_start_date": job_start_date.isoformat(),
                    "source": "salesnav-clay-basic",
                },
                on_conflict="person_linkedin_url,source"
            ).execute()
            result["job_start_date_id"] = "upserted"

        result["success"] = True
        return result

    except Exception as e:
        import traceback
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        return result
