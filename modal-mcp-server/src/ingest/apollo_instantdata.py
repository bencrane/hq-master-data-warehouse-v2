"""
Apollo InstantData Scrape Extraction Endpoint

Extracts person/company data from Apollo instant-data-scraper records.
Splits into extracted.apollo_companies and extracted.apollo_people.
Junction tables track which searches matched each record.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class ApolloInstantDataRequest(BaseModel):
    # Raw record fields (matching raw.apollo_instantdata_scrapes)
    id: Optional[str] = None  # raw_record_id
    scrape_settings_id: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    linkedin_url: Optional[str] = None
    person_location: Optional[str] = None
    photo_url: Optional[str] = None
    apollo_person_url: Optional[str] = None
    apollo_company_url: Optional[str] = None
    company_name: Optional[str] = None
    company_headcount: Optional[str] = None
    industry: Optional[str] = None
    extra_data: Optional[dict] = None
    created_at: Optional[str] = None
    raw_row: Optional[dict] = None


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
def extract_apollo_instantdata(request: ApolloInstantDataRequest) -> dict:
    """
    Extract Apollo instant-data-scraper record into companies and people tables.

    1. Upsert company to extracted.apollo_companies (by apollo_company_url)
    2. Upsert person to extracted.apollo_people (by linkedin_url, if exists)
    3. Insert into junction tables to track search/signal associations
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    company_id = None
    person_id = None

    try:
        apollo_company_url = normalize_null_string(request.apollo_company_url)
        linkedin_url = normalize_null_string(request.linkedin_url)
        scrape_settings_id = normalize_null_string(request.scrape_settings_id)
        raw_record_id = normalize_null_string(request.id)

        # 1. Upsert company (if apollo_company_url exists)
        if apollo_company_url:
            company_data = {
                "apollo_company_url": apollo_company_url,
                "company_name": normalize_null_string(request.company_name),
                "company_headcount": normalize_null_string(request.company_headcount),
                "industry": normalize_null_string(request.industry),
                "last_seen_at": "now()",
            }

            company_result = (
                supabase.schema("extracted")
                .from_("apollo_companies")
                .upsert(company_data, on_conflict="apollo_company_url")
                .execute()
            )

            if company_result.data:
                company_id = company_result.data[0]["id"]

            # Insert company match (junction table)
            if company_id and scrape_settings_id:
                try:
                    supabase.schema("extracted").from_("apollo_company_matches").upsert(
                        {
                            "company_id": company_id,
                            "scrape_settings_id": scrape_settings_id,
                            "raw_record_id": raw_record_id,
                        },
                        on_conflict="company_id,scrape_settings_id"
                    ).execute()
                except Exception:
                    pass  # Ignore duplicate constraint errors

        # 2. Upsert person (if linkedin_url exists)
        if linkedin_url:
            person_data = {
                "linkedin_url": linkedin_url,
                "company_id": company_id,
                "full_name": normalize_null_string(request.full_name),
                "job_title": normalize_null_string(request.job_title),
                "person_location": normalize_null_string(request.person_location),
                "photo_url": normalize_null_string(request.photo_url),
                "apollo_person_url": normalize_null_string(request.apollo_person_url),
                "last_seen_at": "now()",
            }

            person_result = (
                supabase.schema("extracted")
                .from_("apollo_people")
                .upsert(person_data, on_conflict="linkedin_url")
                .execute()
            )

            if person_result.data:
                person_id = person_result.data[0]["id"]

            # Insert person match (junction table)
            if person_id and scrape_settings_id:
                try:
                    supabase.schema("extracted").from_("apollo_person_matches").upsert(
                        {
                            "person_id": person_id,
                            "scrape_settings_id": scrape_settings_id,
                            "raw_record_id": raw_record_id,
                        },
                        on_conflict="person_id,scrape_settings_id"
                    ).execute()
                except Exception:
                    pass  # Ignore duplicate constraint errors

        return {
            "success": True,
            "company_id": company_id,
            "person_id": person_id,
            "had_linkedin_url": linkedin_url is not None,
            "had_company_url": apollo_company_url is not None,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
