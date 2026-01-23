"""
VC Portfolio Ingest - store and match VC portfolio companies

Stores portfolio company data and matches to crunchbase_domain_inference
to populate linkedin_company_url for companies missing it.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class VCPortfolioRequest(BaseModel):
    company_name: str  # Required
    vc_name: Optional[str] = None
    domain: Optional[str] = None
    linkedin_url: Optional[str] = None
    short_description: Optional[str] = None
    long_description: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    employee_range: Optional[str] = None
    founded_date: Optional[str] = None
    operating_status: Optional[str] = None
    workflow_slug: Optional[str] = "vc-portfolio"
    clay_table_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_vc_portfolio(request: VCPortfolioRequest) -> dict:
    """
    Ingest VC portfolio company data.
    
    1. Stores raw payload
    2. Extracts to extracted.vc_portfolio
    3. Attempts to match company_name to crunchbase_domain_inference
    4. If matched, updates linkedin_company_url on crunchbase_domain_inference
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build raw payload
        raw_payload = {
            "vc_name": request.vc_name,
            "company_name": request.company_name,
            "domain": request.domain,
            "linkedin_url": request.linkedin_url,
            "short_description": request.short_description,
            "long_description": request.long_description,
            "city": request.city,
            "state": request.state,
            "country": request.country,
            "employee_range": request.employee_range,
            "founded_date": request.founded_date,
            "operating_status": request.operating_status,
        }

        # Store raw
        raw_result = (
            supabase.schema("raw")
            .from_("vc_portfolio_payloads")
            .insert({
                "vc_name": request.vc_name,
                "company_name": request.company_name,
                "domain": request.domain,
                "linkedin_url": request.linkedin_url,
                "short_description": request.short_description,
                "long_description": request.long_description,
                "city": request.city,
                "state": request.state,
                "country": request.country,
                "employee_range": request.employee_range,
                "founded_date": request.founded_date,
                "operating_status": request.operating_status,
                "workflow_slug": request.workflow_slug,
                "raw_payload": raw_payload,
            })
            .execute()
        )

        raw_payload_id = raw_result.data[0]["id"]

        # Try to match to crunchbase_domain_inference by domain
        matched_domain = None
        match_confidence = None
        linkedin_updated = False

        if request.domain:
            match_result = (
                supabase.schema("extracted")
                .from_("crunchbase_domain_inference")
                .select("inferred_domain, company_name, linkedin_company_url")
                .eq("inferred_domain", request.domain)
                .is_("linkedin_company_url", "null")
                .limit(1)
                .execute()
            )

            if match_result.data and len(match_result.data) > 0:
                matched_domain = match_result.data[0]["inferred_domain"]
                match_confidence = "exact_domain"

                # Update linkedin_company_url if we have a linkedin_url
                if request.linkedin_url:
                    update_result = (
                        supabase.schema("extracted")
                        .from_("crunchbase_domain_inference")
                        .update({"linkedin_company_url": request.linkedin_url})
                        .eq("inferred_domain", request.domain)
                        .is_("linkedin_company_url", "null")
                        .execute()
                    )
                    linkedin_updated = True

        # Store extracted
        extracted_result = (
            supabase.schema("extracted")
            .from_("vc_portfolio")
            .insert({
                "raw_payload_id": raw_payload_id,
                "vc_name": request.vc_name,
                "company_name": request.company_name,
                "domain": request.domain,
                "linkedin_url": request.linkedin_url,
                "short_description": request.short_description,
                "long_description": request.long_description,
                "city": request.city,
                "state": request.state,
                "country": request.country,
                "employee_range": request.employee_range,
                "founded_date": request.founded_date,
                "operating_status": request.operating_status,
                "matched_domain": matched_domain,
                "match_confidence": match_confidence,
            })
            .execute()
        )

        return {
            "success": True,
            "raw_payload_id": raw_payload_id,
            "extracted_id": extracted_result.data[0]["id"],
            "matched_domain": matched_domain,
            "match_confidence": match_confidence,
            "linkedin_updated": linkedin_updated,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
