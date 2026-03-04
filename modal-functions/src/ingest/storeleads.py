"""
Storeleads Ingest Endpoint

Expects:
{
  "domain": "hm.com",
  "raw_payload": {}
}
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class StoreleadsRequest(BaseModel):
    domain: str
    raw_payload: dict


class StoreleadsResponse(BaseModel):
    success: bool
    domain: Optional[str] = None
    raw_payload_id: Optional[str] = None
    extracted_company_id: Optional[str] = None
    technologies_extracted: Optional[int] = None
    error: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_storeleads(request: StoreleadsRequest) -> dict:
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.domain.lower().strip()
        payload = request.raw_payload

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # The payload is nested under "domain" key from Storeleads
        domain_data = payload.get("domain", payload)

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("storeleads_payloads")
            .insert({
                "domain": domain,
                "payload": payload,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Extract LinkedIn URL from contact_info
        linkedin_url = None
        contact_info = domain_data.get("contact_info", [])
        for contact in contact_info:
            if isinstance(contact, dict) and contact.get("type") == "linkedin":
                linkedin_url = contact.get("value")
                break

        # 3. Extract trustpilot data
        trustpilot = domain_data.get("trustpilot", {}) or {}
        trustpilot_avg_rating = trustpilot.get("avg_rating")
        trustpilot_review_count = trustpilot.get("review_count")

        # 4. Insert extracted company data
        company_insert = (
            supabase.schema("extracted")
            .from_("storeleads_company")
            .insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "city": domain_data.get("city"),
                "location": domain_data.get("location"),
                "country_code": domain_data.get("country_code"),
                "region": domain_data.get("region"),
                "subregion": domain_data.get("subregion"),
                "administrative_area_level_1": domain_data.get("administrative_area_level_1"),
                "latitude": domain_data.get("latitude"),
                "longitude": domain_data.get("longitude"),
                "title": domain_data.get("title"),
                "description": domain_data.get("description"),
                "platform": domain_data.get("platform"),
                "employee_count": domain_data.get("employee_count"),
                "product_count": domain_data.get("product_count"),
                "estimated_sales": domain_data.get("estimated_sales"),
                "estimated_sales_yearly": domain_data.get("estimated_sales_yearly"),
                "estimated_visits": domain_data.get("estimated_visits"),
                "estimated_page_views": domain_data.get("estimated_page_views"),
                "rank": domain_data.get("rank"),
                "cc_rank": domain_data.get("cc_rank"),
                "cc_centrality": domain_data.get("cc_centrality"),
                "platform_rank": domain_data.get("platform_rank"),
                "rank_percentile": domain_data.get("rank_percentile"),
                "platform_rank_percentile": domain_data.get("platform_rank_percentile"),
                "trustpilot_avg_rating": trustpilot_avg_rating,
                "trustpilot_review_count": trustpilot_review_count,
                "categories": domain_data.get("categories"),
                "features": domain_data.get("features"),
                "shipping_carriers": domain_data.get("shipping_carriers"),
                "cluster_domains": domain_data.get("cluster_domains"),
                "aliases": domain_data.get("aliases"),
                "redirects_to": domain_data.get("redirects_to"),
                "contact_info": contact_info,
                "linkedin_url": linkedin_url,
                "about_us": domain_data.get("about_us"),
                "career_page": domain_data.get("career_page"),
                "contact_page": domain_data.get("contact_page"),
                "brands_page": domain_data.get("brands_page"),
                "tracking_page": domain_data.get("tracking_page"),
                "store_locator_page": domain_data.get("store_locator_page"),
                "og_image": domain_data.get("og_image"),
                "icon": domain_data.get("icon"),
                "language_code": domain_data.get("language_code"),
                "state": domain_data.get("state"),
                "last_updated_at": domain_data.get("last_updated_at"),
            })
            .execute()
        )
        extracted_company_id = company_insert.data[0]["id"]

        # 5. Extract technologies
        technologies = domain_data.get("technologies", [])
        technologies_extracted = 0
        for tech in technologies:
            if not isinstance(tech, dict):
                continue

            supabase.schema("extracted").from_("storeleads_technology").insert({
                "raw_payload_id": raw_payload_id,
                "storeleads_company_id": extracted_company_id,
                "domain": domain,
                "name": tech.get("name"),
                "icon_url": tech.get("icon_url"),
                "vendor_url": tech.get("vendor_url"),
                "description": tech.get("description"),
                "installs": tech.get("installs"),
                "categories": tech.get("categories"),
                "installed_at": tech.get("installed_at"),
            }).execute()
            technologies_extracted += 1

        # 6. Upsert to core.company_linkedin_urls (if we have one)
        if linkedin_url:
            supabase.schema("core").from_("company_linkedin_urls").upsert({
                "domain": domain,
                "linkedin_url": linkedin_url,
                "source": "storeleads",
            }, on_conflict="domain").execute()

        # 8. Upsert to core.company_employee_ranges (if we have employee_count)
        employee_count = domain_data.get("employee_count")
        if employee_count:
            supabase.schema("core").from_("company_employee_ranges").upsert({
                "domain": domain,
                "source": "storeleads",
                "raw_employee_count": employee_count,
            }, on_conflict="domain,source").execute()

        # 9. Upsert to core.company_revenue (if we have estimated_sales_yearly)
        estimated_sales_yearly = domain_data.get("estimated_sales_yearly")
        if estimated_sales_yearly:
            supabase.schema("core").from_("company_revenue").upsert({
                "domain": domain,
                "source": "storeleads",
                "raw_revenue_amount": int(estimated_sales_yearly),
            }, on_conflict="domain,source").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "extracted_company_id": str(extracted_company_id),
            "technologies_extracted": technologies_extracted,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain if request.domain else "unknown",
        }
