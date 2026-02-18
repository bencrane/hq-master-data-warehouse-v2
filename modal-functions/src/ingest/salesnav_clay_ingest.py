"""
SalesNav Clay Ingestion Endpoint

Ingests SalesNav person data from Clay webhooks following the raw -> extracted -> core pattern.

Data flow:
1. Raw: Store full Clay payload to raw.salesnav_scrapes_person_payloads
2. Extracted: Flatten to extracted.salesnav_scrapes_person
3. Core:
   - core.companies: Upsert current employer (from Company website domain)
   - core.company_linkedin_urls: Store company LinkedIn URL
   - core.person_past_employer: Insert alumni relationship (if ex_company_domain provided)

Note: SalesNav LinkedIn URLs are hashed/sales-specific, NOT real profile URLs.
We store them as person_linkedin_sales_nav_url, not linkedin_url.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class SalesNavClayRequest(BaseModel):
    """Request model for Clay SalesNav webhook."""
    raw_payload: dict  # Full Clay payload with fields like "First name", "Company website", etc.
    ex_company_domain: Optional[str] = None  # Direct alumni domain (e.g., "palantir.com")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_clay(request: SalesNavClayRequest) -> dict:
    """
    Ingest SalesNav person data from Clay webhook.

    1. Stores raw payload to raw.salesnav_scrapes_person_payloads
    2. Extracts flattened data to extracted.salesnav_scrapes_person
    3. If ex_company_domain provided, inserts to core.person_past_employer

    Returns:
        {
            "success": true,
            "raw_id": "uuid",
            "extracted_person_id": "uuid",
            "past_employer_inserted": true/false,
            "ex_company_domain": "palantir.com"
        }
    """
    from supabase import create_client
    from extraction.salesnav_clay import (
        extract_salesnav_clay_person,
        normalize_null_string,
        extract_domain_from_url,
    )

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        payload = request.raw_payload

        # Get LinkedIn URL for raw table key
        linkedin_url = normalize_null_string(
            payload.get("LinkedIn URL (user profile)") or
            payload.get("person_linkedin_sales_nav_url")
        )
        linkedin_urn = normalize_null_string(payload.get("LinkedIn user profile URN"))

        # Extract domain from Company website
        company_website = normalize_null_string(payload.get("Company website"))
        domain = extract_domain_from_url(company_website)

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("salesnav_scrapes_person_payloads")
            .insert({
                "person_linkedin_sales_nav_url": linkedin_url,
                "linkedin_user_profile_urn": linkedin_urn,
                "domain": domain,
                "workflow_slug": "salesnav-clay",
                "raw_payload": payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # 2. Extract to extracted.salesnav_scrapes_person
        extracted_result = extract_salesnav_clay_person(
            supabase=supabase,
            raw_payload_id=raw_id,
            payload=payload,
        )
        extracted_person_id = extracted_result["id"] if extracted_result else None

        # 3. Upsert current employer to core.companies
        company_id = None
        company_name = normalize_null_string(payload.get("Company"))
        company_linkedin_url = normalize_null_string(payload.get("LinkedIn URL (company)"))

        if domain:
            # Check if company exists
            existing_company = (
                supabase.schema("core")
                .from_("companies")
                .select("id")
                .eq("domain", domain)
                .execute()
            )

            if existing_company.data:
                company_id = existing_company.data[0]["id"]
            else:
                # Insert new company
                company_insert = (
                    supabase.schema("core")
                    .from_("companies")
                    .insert({
                        "domain": domain,
                        "name": company_name,
                    })
                    .execute()
                )
                company_id = company_insert.data[0]["id"] if company_insert.data else None

        # 4. Upsert company LinkedIn URL to core.company_linkedin_urls
        if domain and company_linkedin_url:
            supabase.schema("core").from_("company_linkedin_urls").upsert(
                {
                    "domain": domain,
                    "linkedin_url": company_linkedin_url,
                    "source": "salesnav-clay",
                },
                on_conflict="domain"
            ).execute()

        # 5. Insert to extracted.salesnav_scrapes_companies
        extracted_company_id = None
        if domain:
            company_description = normalize_null_string(payload.get("Company description"))
            company_headcount = normalize_null_string(payload.get("Company headcount"))
            company_industries = normalize_null_string(payload.get("Company industries"))
            company_address = normalize_null_string(payload.get("Company registered address"))
            company_linkedin_urn = normalize_null_string(payload.get("Linkedin company profile URN"))

            # Parse headcount to int
            headcount_int = None
            if company_headcount:
                try:
                    headcount_int = int(str(company_headcount).replace(",", ""))
                except (ValueError, TypeError):
                    pass

            extracted_company_data = {
                "company_name": company_name,
                "linkedin_url": company_linkedin_url,
                "linkedin_urn": company_linkedin_urn,
                "domain": domain,
                "description": company_description,
                "headcount": headcount_int,
                "industries": company_industries,
                "registered_address_raw": company_address,
            }

            extracted_company_result = (
                supabase.schema("extracted")
                .from_("salesnav_scrapes_companies")
                .insert(extracted_company_data)
                .execute()
            )
            extracted_company_id = extracted_company_result.data[0]["id"] if extracted_company_result.data else None

        # 6. Insert to core.person_past_employer if ex_company_domain provided
        past_employer_inserted = False
        ex_domain = normalize_null_string(request.ex_company_domain)

        if ex_domain and linkedin_url:
            # Get person's first/last name for the record
            first_name = normalize_null_string(payload.get("First name"))
            last_name = normalize_null_string(payload.get("Last name"))

            past_employer_data = {
                "linkedin_url": linkedin_url,
                "past_company_name": None,  # Not known from export_title
                "past_company_domain": ex_domain.lower(),
                "source": "salesnav-clay",
            }

            # Upsert with correct 3-column constraint
            supabase.schema("core").from_("person_past_employer").upsert(
                past_employer_data,
                on_conflict="linkedin_url,past_company_name,past_company_domain"
            ).execute()
            past_employer_inserted = True

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_person_id": extracted_person_id,
            "extracted_company_id": extracted_company_id,
            "core_company_id": company_id,
            "company_domain": domain,
            "past_employer_inserted": past_employer_inserted,
            "ex_company_domain": ex_domain,
        }

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
