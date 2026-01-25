"""
Apollo Scrape Ingestion Endpoint

Ingests person/company data from Apollo scrapes.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class ApolloScrapeRequest(BaseModel):
    # Top-level cleaned fields
    cleaned_company_name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    cleaned_first_name: Optional[str] = None
    cleaned_last_name: Optional[str] = None
    cleaned_full_name: Optional[str] = None
    workflow_slug: Optional[str] = "apollo-scrape"
    
    # Apollo fields (direct from scrape)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    headline: Optional[str] = None
    seniority: Optional[str] = None
    email: Optional[str] = None
    email_status: Optional[str] = None
    person_linkedin_link: Optional[str] = None
    lead_city: Optional[str] = None
    lead_state: Optional[str] = None
    lead_country: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    departments: Optional[str] = None
    subdepartments: Optional[str] = None
    functions: Optional[str] = None
    company_website_full: Optional[str] = None
    company_linkedin_link: Optional[str] = None
    company_phone_number: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_country: Optional[str] = None
    company_postal_code: Optional[str] = None
    company_address: Optional[str] = None
    company_annual_revenue: Optional[str] = None
    company_total_funding: Optional[str] = None
    company_latest_funding_type: Optional[str] = None
    company_latest_funding_amount: Optional[str] = None
    last_fund_raised_at: Optional[str] = None
    company_founded_year: Optional[str] = None
    company_short_description: Optional[str] = None
    company_seo_description: Optional[str] = None
    number_of_retail_locations: Optional[str] = None
    company_market_cap: Optional[str] = None
    is_likely_to_engage: Optional[str] = None
    company_blog_link: Optional[str] = None
    company_twitter_link: Optional[str] = None
    company_facebook_link: Optional[str] = None
    company_street: Optional[str] = None
    company_keywords: Optional[str] = None
    company_technologies: Optional[str] = None


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
def ingest_apollo_scrape(request: ApolloScrapeRequest) -> dict:
    """
    Ingest Apollo scrape data.
    Stores raw payload, then extracts key fields.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build raw payload from all fields
        raw_payload = request.model_dump()

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("apollo_scrape")
            .insert({
                "domain": request.domain,
                "cleaned_company_name": request.cleaned_company_name,
                "linkedin_url": request.linkedin_url,
                "workflow_slug": request.workflow_slug,
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        extracted_data = {
            "raw_payload_id": raw_id,
            "cleaned_company_name": normalize_null_string(request.cleaned_company_name),
            "domain": normalize_null_string(request.domain),
            "linkedin_url": normalize_null_string(request.linkedin_url),
            "cleaned_first_name": normalize_null_string(request.cleaned_first_name),
            "cleaned_last_name": normalize_null_string(request.cleaned_last_name),
            "cleaned_full_name": normalize_null_string(request.cleaned_full_name),
            "first_name": normalize_null_string(request.first_name),
            "last_name": normalize_null_string(request.last_name),
            "full_name": normalize_null_string(request.full_name),
            "title": normalize_null_string(request.title),
            "headline": normalize_null_string(request.headline),
            "seniority": normalize_null_string(request.seniority),
            "email": normalize_null_string(request.email),
            "email_status": normalize_null_string(request.email_status),
            "person_linkedin_url": normalize_null_string(request.person_linkedin_link),
            "lead_city": normalize_null_string(request.lead_city),
            "lead_state": normalize_null_string(request.lead_state),
            "lead_country": normalize_null_string(request.lead_country),
            "company_name": normalize_null_string(request.company_name),
            "industry": normalize_null_string(request.industry),
            "employee_count": normalize_null_string(request.employee_count),
            "departments": normalize_null_string(request.departments),
            "subdepartments": normalize_null_string(request.subdepartments),
            "functions": normalize_null_string(request.functions),
            "company_website": normalize_null_string(request.company_website_full),
            "company_linkedin_url": normalize_null_string(request.company_linkedin_link),
            "company_phone": normalize_null_string(request.company_phone_number),
            "company_city": normalize_null_string(request.company_city),
            "company_state": normalize_null_string(request.company_state),
            "company_country": normalize_null_string(request.company_country),
            "company_postal_code": normalize_null_string(request.company_postal_code),
            "company_address": normalize_null_string(request.company_address),
            "company_annual_revenue": normalize_null_string(request.company_annual_revenue),
            "company_total_funding": normalize_null_string(request.company_total_funding),
            "company_latest_funding_type": normalize_null_string(request.company_latest_funding_type),
            "company_latest_funding_amount": normalize_null_string(request.company_latest_funding_amount),
            "last_fund_raised_at": normalize_null_string(request.last_fund_raised_at),
            "company_founded_year": normalize_null_string(request.company_founded_year),
            "company_short_description": normalize_null_string(request.company_short_description),
            "company_seo_description": normalize_null_string(request.company_seo_description),
            "number_of_retail_locations": normalize_null_string(request.number_of_retail_locations),
            "company_market_cap": normalize_null_string(request.company_market_cap),
            "is_likely_to_engage": normalize_null_string(request.is_likely_to_engage),
            "company_blog_link": normalize_null_string(request.company_blog_link),
            "company_twitter_link": normalize_null_string(request.company_twitter_link),
            "company_facebook_link": normalize_null_string(request.company_facebook_link),
            "company_street": normalize_null_string(request.company_street),
            "company_keywords": normalize_null_string(request.company_keywords),
            "company_technologies": normalize_null_string(request.company_technologies),
        }

        extracted_insert = (
            supabase.schema("extracted")
            .from_("apollo_scrape")
            .insert(extracted_data)
            .execute()
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_insert.data[0]["id"] if extracted_insert.data else None,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
