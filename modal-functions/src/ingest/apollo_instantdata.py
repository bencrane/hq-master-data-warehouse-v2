"""
Apollo InstantData Scrape Extraction Endpoint

Extracts person/company data from Apollo instant-data-scraper records.
Simple approach: one row per record, no deduplication at insert time.
Dedupe at query time using views or DISTINCT ON.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class ApolloInstantDataRequest(BaseModel):
    # Raw record fields
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
    created_at: Optional[str] = None


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
    Extract Apollo instant-data-scraper record into people and companies tables.

    Simple INSERT (no deduplication). Each record keeps its scrape_settings_id.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    person_id = None
    company_id = None

    try:
        scrape_settings_id = normalize_null_string(request.scrape_settings_id)
        raw_record_id = normalize_null_string(request.id)
        source_created_at = normalize_null_string(request.created_at)

        if not scrape_settings_id:
            return {"success": False, "error": "scrape_settings_id is required"}

        # 1. Insert person record
        person_data = {
            "scrape_settings_id": scrape_settings_id,
            "raw_record_id": raw_record_id,
            "linkedin_url": normalize_null_string(request.linkedin_url),
            "full_name": normalize_null_string(request.full_name),
            "job_title": normalize_null_string(request.job_title),
            "person_location": normalize_null_string(request.person_location),
            "photo_url": normalize_null_string(request.photo_url),
            "apollo_person_url": normalize_null_string(request.apollo_person_url),
            "company_name": normalize_null_string(request.company_name),
            "company_headcount": normalize_null_string(request.company_headcount),
            "industry": normalize_null_string(request.industry),
            "apollo_company_url": normalize_null_string(request.apollo_company_url),
            "source_created_at": source_created_at,
        }

        person_result = (
            supabase.schema("extracted")
            .from_("apollo_instantdata_people")
            .insert(person_data)
            .execute()
        )

        if person_result.data:
            person_id = person_result.data[0]["id"]

        # 2. Insert company record (if apollo_company_url exists)
        apollo_company_url = normalize_null_string(request.apollo_company_url)
        if apollo_company_url:
            company_data = {
                "scrape_settings_id": scrape_settings_id,
                "raw_record_id": raw_record_id,
                "apollo_company_url": apollo_company_url,
                "company_name": normalize_null_string(request.company_name),
                "company_headcount": normalize_null_string(request.company_headcount),
                "industry": normalize_null_string(request.industry),
                "source_created_at": source_created_at,
            }

            company_result = (
                supabase.schema("extracted")
                .from_("apollo_instantdata_companies")
                .insert(company_data)
                .execute()
            )

            if company_result.data:
                company_id = company_result.data[0]["id"]

        return {
            "success": True,
            "person_id": person_id,
            "company_id": company_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
