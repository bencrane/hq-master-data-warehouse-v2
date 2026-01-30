"""
ICP Verdict Ingest

Modal endpoint for receiving ICP verdict payloads from Clay.
Stores raw payload, then extracts normalized data.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class ICPVerdictRequest(BaseModel):
    origin_company_domain: str
    company_domain: str
    workflow_slug: str
    # Verdict fields - support both formats
    label: Optional[str] = None
    verdict: Optional[str] = None
    rationale: Optional[str] = None
    reason: Optional[str] = None
    # Token/cost fields (optional)
    tokensUsed: Optional[int] = None
    inputTokens: Optional[int] = None
    outputTokens: Optional[int] = None
    totalCostToAIProvider: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_icp_verdict(request: ICPVerdictRequest) -> dict:
    """
    Ingest ICP verdict payload from Clay.
    
    1. Stores raw payload in raw.icp_verdict_payloads
    2. Calls extraction to normalize into extracted.icp_verdict
    """
    from supabase import create_client
    from extraction.icp_verdict import extract_icp_verdict

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build the payload from all verdict-related fields
        payload = {}
        if request.label is not None:
            payload["label"] = request.label
        if request.verdict is not None:
            payload["verdict"] = request.verdict
        if request.rationale is not None:
            payload["rationale"] = request.rationale
        if request.reason is not None:
            payload["reason"] = request.reason
        if request.tokensUsed is not None:
            payload["tokensUsed"] = request.tokensUsed
        if request.inputTokens is not None:
            payload["inputTokens"] = request.inputTokens
        if request.outputTokens is not None:
            payload["outputTokens"] = request.outputTokens
        if request.totalCostToAIProvider is not None:
            payload["totalCostToAIProvider"] = request.totalCostToAIProvider

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("icp_verdict_payloads")
            .insert({
                "origin_company_domain": request.origin_company_domain,
                "company_domain": request.company_domain,
                "payload": payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract normalized data
        extracted_id, is_match = extract_icp_verdict(
            supabase=supabase,
            raw_payload_id=raw_id,
            origin_company_domain=request.origin_company_domain,
            company_domain=request.company_domain,
            payload=payload,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "is_match": is_match,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
