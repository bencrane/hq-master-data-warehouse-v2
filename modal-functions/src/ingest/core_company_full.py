"""
Core Company Full Upsert

Accepts enriched company data and upserts to all core dimension tables:
- core.companies
- core.company_locations
- core.company_industries
- core.company_employee_ranges
- core.company_linkedin_urls
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from config import app, image


class CoreCompanyFullRequest(BaseModel):
    company_name: str
    domain: str
    linkedin_url: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    employee_range: Optional[str] = None
    source: str = "gemini-enrichment"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def upsert_core_company_full(request: CoreCompanyFullRequest) -> dict:
    """
    Upsert enriched company data to all core dimension tables.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    now = datetime.utcnow().isoformat()
    results = {}

    try:
        # 1. Upsert to core.companies
        company_result = (
            supabase.schema("core")
            .from_("companies")
            .upsert({
                "domain": request.domain,
                "name": request.company_name,
                "linkedin_url": request.linkedin_url,
                "updated_at": now,
            }, on_conflict="domain")
            .execute()
        )
        results["company_id"] = company_result.data[0]["id"] if company_result.data else None

        # 2. Upsert to core.company_locations (if location data provided)
        if request.city or request.state or request.country:
            location_result = (
                supabase.schema("core")
                .from_("company_locations")
                .upsert({
                    "domain": request.domain,
                    "city": request.city,
                    "state": request.state,
                    "country": request.country,
                    "source": request.source,
                    "has_city": bool(request.city),
                    "has_state": bool(request.state),
                    "updated_at": now,
                }, on_conflict="domain")
                .execute()
            )
            results["location_id"] = location_result.data[0]["id"] if location_result.data else None

        # 3. Upsert to core.company_industries (if industry provided)
        if request.industry:
            industry_result = (
                supabase.schema("core")
                .from_("company_industries")
                .upsert({
                    "domain": request.domain,
                    "matched_industry": request.industry,
                    "source": request.source,
                    "updated_at": now,
                }, on_conflict="domain")
                .execute()
            )
            results["industry_id"] = industry_result.data[0]["id"] if industry_result.data else None

        # 4. Upsert to core.company_employee_ranges (if employee_range provided)
        if request.employee_range:
            employee_result = (
                supabase.schema("core")
                .from_("company_employee_ranges")
                .upsert({
                    "domain": request.domain,
                    "matched_employee_range": request.employee_range,
                    "source": request.source,
                    "updated_at": now,
                }, on_conflict="domain,source")
                .execute()
            )
            results["employee_range_id"] = employee_result.data[0]["id"] if employee_result.data else None

        # 5. Upsert to core.company_linkedin_urls (if linkedin_url provided)
        if request.linkedin_url:
            linkedin_result = (
                supabase.schema("core")
                .from_("company_linkedin_urls")
                .upsert({
                    "domain": request.domain,
                    "linkedin_url": request.linkedin_url,
                    "source": request.source,
                    "updated_at": now,
                }, on_conflict="domain")
                .execute()
            )
            results["linkedin_url_id"] = linkedin_result.data[0]["id"] if linkedin_result.data else None

        return {
            "success": True,
            "domain": request.domain,
            **results,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
