"""
CB VC Portfolio Data Ingest

Ingests Crunchbase VC portfolio company data and stores in raw + extracted tables.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.cb_vc_portfolio import extract_cb_vc_portfolio


class CbVcPortfolioRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    short_description: Optional[str] = None
    employee_range: Optional[str] = None
    last_funding_date: Optional[str] = None
    last_funding_type: Optional[str] = None
    last_funding_amount: Optional[str] = None
    last_equity_funding_type: Optional[str] = None
    last_leadership_hiring_date: Optional[str] = None
    founded_date: Optional[str] = None
    estimated_revenue_range: Optional[str] = None
    funding_status: Optional[str] = None
    total_funding_amount: Optional[str] = None
    total_equity_funding_amount: Optional[str] = None
    operating_status: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    vc: Optional[str] = None
    vc1: Optional[str] = None
    vc2: Optional[str] = None
    vc3: Optional[str] = None
    vc4: Optional[str] = None
    vc5: Optional[str] = None
    vc6: Optional[str] = None
    vc7: Optional[str] = None
    vc8: Optional[str] = None
    vc9: Optional[str] = None
    vc10: Optional[str] = None
    vc11: Optional[str] = None
    vc12: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_cb_vc_portfolio(request: CbVcPortfolioRequest) -> dict:
    """
    Ingest CB VC portfolio data.
    Stores raw payload, then extracts one row per VC to extracted table.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("cb_vc_portfolio_payloads")
            .insert({
                "company_name": request.company_name,
                "domain": request.domain,
                "city": request.city,
                "state": request.state,
                "country": request.country,
                "short_description": request.short_description,
                "employee_range": request.employee_range,
                "last_funding_date": request.last_funding_date,
                "last_funding_type": request.last_funding_type,
                "last_funding_amount": request.last_funding_amount,
                "last_equity_funding_type": request.last_equity_funding_type,
                "last_leadership_hiring_date": request.last_leadership_hiring_date,
                "founded_date": request.founded_date,
                "estimated_revenue_range": request.estimated_revenue_range,
                "funding_status": request.funding_status,
                "total_funding_amount": request.total_funding_amount,
                "total_equity_funding_amount": request.total_equity_funding_amount,
                "operating_status": request.operating_status,
                "company_linkedin_url": request.company_linkedin_url,
                "vc": request.vc,
                "vc1": request.vc1,
                "vc2": request.vc2,
                "vc3": request.vc3,
                "vc4": request.vc4,
                "vc5": request.vc5,
                "vc6": request.vc6,
                "vc7": request.vc7,
                "vc8": request.vc8,
                "vc9": request.vc9,
                "vc10": request.vc10,
                "vc11": request.vc11,
                "vc12": request.vc12,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Collect all VC names
        vc_names = [
            request.vc, request.vc1, request.vc2, request.vc3, request.vc4,
            request.vc5, request.vc6, request.vc7, request.vc8, request.vc9,
            request.vc10, request.vc11, request.vc12
        ]

        # Extract one row per VC
        vc_count = extract_cb_vc_portfolio(
            supabase,
            raw_id,
            request.company_name,
            request.domain,
            request.city,
            request.state,
            request.country,
            request.short_description,
            request.employee_range,
            request.last_funding_date,
            request.last_funding_type,
            request.last_funding_amount,
            request.last_equity_funding_type,
            request.last_leadership_hiring_date,
            request.founded_date,
            request.estimated_revenue_range,
            request.funding_status,
            request.total_funding_amount,
            request.total_equity_funding_amount,
            request.operating_status,
            request.company_linkedin_url,
            vc_names,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "vc_count": vc_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
