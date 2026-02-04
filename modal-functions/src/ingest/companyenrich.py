"""
CompanyEnrich.com Company Enrichment Ingestion Endpoint

Ingests company enrichment data from companyenrich.com.
Stores raw payload and extracts to multiple breakout tables.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List
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


def parse_investors(investors_str: Optional[str]) -> List[str]:
    """Parse comma-separated investors string into list."""
    if not investors_str:
        return []
    return [inv.strip() for inv in investors_str.split(",") if inv.strip()]


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_companyenrich(request: CompanyEnrichRequest) -> dict:
    """
    Ingest CompanyEnrich.com company enrichment data.

    Stores raw payload and extracts to:
    - companyenrich_company (main firmographics)
    - companyenrich_keywords
    - companyenrich_technologies
    - companyenrich_industries
    - companyenrich_categories
    - companyenrich_naics_codes
    - companyenrich_funding_rounds
    - companyenrich_investors
    - companyenrich_vc_investments
    - companyenrich_socials
    - companyenrich_location
    - companyenrich_subsidiaries
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        payload = request.raw_payload or {}
        domain = request.domain

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("companyenrich_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract nested objects
        location = payload.get("location") or {}
        socials = payload.get("socials") or {}
        financial = payload.get("financial") or {}
        city_obj = location.get("city") or {}
        state_obj = location.get("state") or {}
        country_obj = location.get("country") or {}

        # 2. Main company table (with arrays for easy retrieval)
        extracted_company = {
            "domain": domain,
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
            # Location (also in breakout)
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
            # Socials (also in breakout)
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

        company_upsert = (
            supabase.schema("extracted")
            .from_("companyenrich_company")
            .upsert(extracted_company, on_conflict="domain")
            .execute()
        )
        extracted_id = company_upsert.data[0]["id"] if company_upsert.data else None

        # 3. Keywords breakout
        keywords = payload.get("keywords") or []
        for kw in keywords:
            if kw:
                try:
                    supabase.schema("extracted").from_("companyenrich_keywords").upsert(
                        {"domain": domain, "keyword": kw},
                        on_conflict="domain,keyword"
                    ).execute()
                except Exception:
                    pass

        # 4. Technologies breakout
        technologies = payload.get("technologies") or []
        for tech in technologies:
            if tech:
                try:
                    supabase.schema("extracted").from_("companyenrich_technologies").upsert(
                        {"domain": domain, "technology": tech},
                        on_conflict="domain,technology"
                    ).execute()
                except Exception:
                    pass

        # 5. Industries breakout
        industries = payload.get("industries") or []
        for ind in industries:
            if ind:
                try:
                    supabase.schema("extracted").from_("companyenrich_industries").upsert(
                        {"domain": domain, "industry": ind},
                        on_conflict="domain,industry"
                    ).execute()
                except Exception:
                    pass

        # 6. Categories breakout
        categories = payload.get("categories") or []
        for cat in categories:
            if cat:
                try:
                    supabase.schema("extracted").from_("companyenrich_categories").upsert(
                        {"domain": domain, "category": cat},
                        on_conflict="domain,category"
                    ).execute()
                except Exception:
                    pass

        # 7. NAICS codes breakout
        naics_codes = payload.get("naics_codes") or []
        for code in naics_codes:
            if code:
                try:
                    supabase.schema("extracted").from_("companyenrich_naics_codes").upsert(
                        {"domain": domain, "naics_code": code},
                        on_conflict="domain,naics_code"
                    ).execute()
                except Exception:
                    pass

        # 8. Funding rounds, investors, and VC investments
        funding_rounds = financial.get("funding") or []
        funding_count = 0
        all_investors = set()

        for round_data in funding_rounds:
            funding_date = parse_datetime(round_data.get("date"))
            funding_type = round_data.get("type")
            amount = round_data.get("amount")
            investors_str = round_data.get("from")

            # Funding round
            try:
                supabase.schema("extracted").from_("companyenrich_funding_rounds").upsert(
                    {
                        "domain": domain,
                        "funding_date": funding_date,
                        "funding_type": funding_type,
                        "amount": amount,
                        "investors": investors_str,
                        "url": round_data.get("url"),
                    },
                    on_conflict="domain,funding_date,funding_type"
                ).execute()
                funding_count += 1
            except Exception:
                pass

            # Parse and insert individual investors
            investors = parse_investors(investors_str)
            for investor in investors:
                all_investors.add(investor)

                # VC Investment record (investor + round details)
                try:
                    supabase.schema("extracted").from_("companyenrich_vc_investments").upsert(
                        {
                            "domain": domain,
                            "investor_name": investor,
                            "funding_date": funding_date,
                            "funding_type": funding_type,
                            "amount": amount,
                        },
                        on_conflict="domain,investor_name,funding_date,funding_type"
                    ).execute()
                except Exception:
                    pass

        # Unique investors list
        for investor in all_investors:
            try:
                supabase.schema("extracted").from_("companyenrich_investors").upsert(
                    {"domain": domain, "investor_name": investor},
                    on_conflict="domain,investor_name"
                ).execute()
            except Exception:
                pass

        # 9. Socials breakout
        if socials:
            try:
                supabase.schema("extracted").from_("companyenrich_socials").upsert(
                    {
                        "domain": domain,
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
                    },
                    on_conflict="domain"
                ).execute()
            except Exception:
                pass

        # 10. Location breakout
        if location:
            try:
                supabase.schema("extracted").from_("companyenrich_location").upsert(
                    {
                        "domain": domain,
                        "address": location.get("address"),
                        "phone": location.get("phone"),
                        "postal_code": location.get("postal_code"),
                        "city": city_obj.get("name"),
                        "city_id": city_obj.get("id"),
                        "state": state_obj.get("name"),
                        "state_code": state_obj.get("code"),
                        "state_id": state_obj.get("id"),
                        "country": country_obj.get("name"),
                        "country_code": country_obj.get("code"),
                        "latitude": city_obj.get("latitude"),
                        "longitude": city_obj.get("longitude"),
                    },
                    on_conflict="domain"
                ).execute()
            except Exception:
                pass

        # 11. Subsidiaries breakout
        subsidiaries = payload.get("subsidiaries") or []
        if subsidiaries:
            for sub in subsidiaries:
                if isinstance(sub, dict):
                    sub_name = sub.get("name")
                    sub_domain = sub.get("domain")
                elif isinstance(sub, str):
                    sub_name = sub
                    sub_domain = None
                else:
                    continue

                if sub_name:
                    try:
                        supabase.schema("extracted").from_("companyenrich_subsidiaries").upsert(
                            {
                                "domain": domain,
                                "subsidiary_name": sub_name,
                                "subsidiary_domain": sub_domain,
                                "subsidiary_data": sub if isinstance(sub, dict) else None,
                            },
                            on_conflict="domain,subsidiary_name"
                        ).execute()
                    except Exception:
                        pass

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "funding_rounds_processed": funding_count,
            "keywords_count": len(keywords),
            "technologies_count": len(technologies),
            "investors_count": len(all_investors),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
