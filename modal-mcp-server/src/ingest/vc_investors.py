"""
Company VC Investors Ingest

Ingest endpoint for company VC investor data from Clay.
Receives a company with up to 12 VC co-investors and explodes them into normalized rows.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.vc_investors import extract_company_vc_investors


class CompanyVCInvestorsRequest(BaseModel):
    company_name: str
    company_domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    vc_og: Optional[str] = None
    vc_1: Optional[str] = None
    vc_2: Optional[str] = None
    vc_3: Optional[str] = None
    vc_4: Optional[str] = None
    vc_5: Optional[str] = None
    vc_6: Optional[str] = None
    vc_7: Optional[str] = None
    vc_8: Optional[str] = None
    vc_9: Optional[str] = None
    vc_10: Optional[str] = None
    vc_11: Optional[str] = None
    vc_12: Optional[str] = None
    workflow_slug: str = "clay-company-vc-investors"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_vc_investors(request: CompanyVCInvestorsRequest) -> dict:
    """
    Ingest company VC investor data.

    1. Looks up workflow in registry
    2. Stores raw payload
    3. Extracts each VC to individual rows
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Look up workflow in registry
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", request.workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found in registry"}

        # Build VC list
        vc_list = [
            request.vc_1, request.vc_2, request.vc_3, request.vc_4,
            request.vc_5, request.vc_6, request.vc_7, request.vc_8,
            request.vc_9, request.vc_10, request.vc_11, request.vc_12,
        ]

        # Build raw payload
        raw_payload = {
            "company_name": request.company_name,
            "company_domain": request.company_domain,
            "company_linkedin_url": request.company_linkedin_url,
            "vc_og": request.vc_og,
            "vc_1": request.vc_1,
            "vc_2": request.vc_2,
            "vc_3": request.vc_3,
            "vc_4": request.vc_4,
            "vc_5": request.vc_5,
            "vc_6": request.vc_6,
            "vc_7": request.vc_7,
            "vc_8": request.vc_8,
            "vc_9": request.vc_9,
            "vc_10": request.vc_10,
            "vc_11": request.vc_11,
            "vc_12": request.vc_12,
        }

        # Store raw payload
        raw_record = {
            "company_name": request.company_name,
            "company_domain": request.company_domain,
            "company_linkedin_url": request.company_linkedin_url,
            "vc_og": request.vc_og,
            "vc_1": request.vc_1,
            "vc_2": request.vc_2,
            "vc_3": request.vc_3,
            "vc_4": request.vc_4,
            "vc_5": request.vc_5,
            "vc_6": request.vc_6,
            "vc_7": request.vc_7,
            "vc_8": request.vc_8,
            "vc_9": request.vc_9,
            "vc_10": request.vc_10,
            "vc_11": request.vc_11,
            "vc_12": request.vc_12,
            "workflow_slug": request.workflow_slug,
            "raw_payload": raw_payload,
        }

        raw_result = (
            supabase.schema("raw")
            .from_("company_vc_investors")
            .insert(raw_record)
            .execute()
        )

        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}

        raw_payload_id = raw_result.data[0]["id"]

        # Extract VCs to individual rows
        vc_count = extract_company_vc_investors(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            company_name=request.company_name,
            company_domain=request.company_domain,
            company_linkedin_url=request.company_linkedin_url,
            vc_og=request.vc_og,
            vc_list=vc_list,
        )

        return {
            "success": True,
            "raw_id": raw_payload_id,
            "vc_count": vc_count,
            "company_name": request.company_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
