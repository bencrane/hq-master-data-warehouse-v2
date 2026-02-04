"""
CompanyEnrich.com Company Enrichment Ingestion Endpoint

Ingests company enrichment data from companyenrich.com.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from config import app, image


class CompanyEnrichRequest(BaseModel):
    domain: str
    raw_payload: dict


def safe_get(d: dict, *keys, default=None):
    """Safely get nested dict values."""
    for key in keys:
        if d is None or not isinstance(d, dict):
            return default
        d = d.get(key)
    return d if d is not None else default


def parse_datetime(dt_str: Optional[str]) -> Optional[str]:
    """Parse datetime string to ISO format."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).isoformat()
    except Exception:
        return None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_companyenrich(request: CompanyEnrichRequest) -> dict:
    """
    Ingest CompanyEnrich.com company enrichment data.
    Stores raw payload, extracts company fields, and extracts funding rounds.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        payload = request.raw_payload or {}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("companyenrich_payloads")
            .insert({
                "domain": request.domain,
                "payload": payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # 2. Extract company data
        location = payload.get("location") or {}
        socials = payload.get("socials") or {}
        financial = payload.get("financial") or {}
        city_obj = location.get("city") or {}
        state_obj = location.get("state") or {}
        country_obj = location.get("country") or {}

        extracted_company = {
            "domain": request.domain,
            "companyenrich_id": payload.get("id"),
            "name": payload.get("name"),
            "type": payload.get("type"),
            "website": payload.get("website"),
            "revenue": payload.get("revenue"),
            "employees": payload.get("employees"),
            "industry": payload.get("industry"),
            "industries": payload.get("industries"),
            "description": payload.get("description"),
            "seo_description": payload.get("seo_description"),
            "founded_year": payload.get("founded_year"),
            "page_rank": payload.get("page_rank"),
            "logo_url": payload.get("logo_url"),
            "categories": payload.get("categories"),
            "keywords": payload.get("keywords"),
            "technologies": payload.get("technologies"),
            "naics_codes": payload.get("naics_codes"),
            # Location
            "address": location.get("address"),
            "phone": location.get("phone"),
            "postal_code": location.get("postal_code"),
            "city": city_obj.get("name"),
            "state": state_obj.get("name"),
            "state_code": state_obj.get("code"),
            "country": country_obj.get("name"),
            "country_code": country_obj.get("code"),
            "latitude": city_obj.get("latitude"),
            "longitude": city_obj.get("longitude"),
            # Socials
            "linkedin_url": socials.get("linkedin_url"),
            "linkedin_id": socials.get("linkedin_id"),
            "twitter_url": socials.get("twitter_url"),
            "facebook_url": socials.get("facebook_url"),
            "github_url": socials.get("github_url"),
            "youtube_url": socials.get("youtube_url"),
            "instagram_url": socials.get("instagram_url"),
            "crunchbase_url": socials.get("crunchbase_url"),
            "g2_url": socials.get("g2_url"),
            "angellist_url": socials.get("angellist_url"),
            # Funding summary
            "total_funding": financial.get("total_funding"),
            "funding_stage": financial.get("funding_stage"),
            "funding_date": parse_datetime(financial.get("funding_date")),
            "stock_symbol": financial.get("stock_symbol"),
            "stock_exchange": financial.get("stock_exchange"),
            # Meta
            "companyenrich_updated_at": parse_datetime(payload.get("updated_at")),
        }

        # Upsert company (update if domain exists)
        company_upsert = (
            supabase.schema("extracted")
            .from_("companyenrich_company")
            .upsert(extracted_company, on_conflict="domain")
            .execute()
        )
        extracted_id = company_upsert.data[0]["id"] if company_upsert.data else None

        # 3. Extract funding rounds
        funding_rounds = financial.get("funding") or []
        funding_count = 0

        for round_data in funding_rounds:
            funding_record = {
                "domain": request.domain,
                "funding_date": parse_datetime(round_data.get("date")),
                "funding_type": round_data.get("type"),
                "amount": round_data.get("amount"),
                "investors": round_data.get("from"),
                "url": round_data.get("url"),
            }
            try:
                supabase.schema("extracted").from_("companyenrich_funding_rounds").upsert(
                    funding_record,
                    on_conflict="domain,funding_date,funding_type"
                ).execute()
                funding_count += 1
            except Exception:
                pass  # Skip duplicates or errors

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "funding_rounds_processed": funding_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
