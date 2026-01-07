"""
Company Ingestion Endpoints

- ingest_clay_company_firmo: Enriched company data (clay-company-firmographics)
- ingest_clay_find_companies: Discovery company data (clay-find-companies)
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# Import app and image from config
from config import app, image

from extraction.company import extract_company_firmographics, extract_find_companies


class CompanyIngestRequest(BaseModel):
    company_domain: str
    workflow_slug: str
    raw_payload: dict


class CompanyDiscoveryRequest(BaseModel):
    company_domain: str
    workflow_slug: str
    raw_payload: dict


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_company_firmo(request: CompanyIngestRequest) -> dict:
    """
    Ingest enriched company payload (clay-company-firmographics workflow).
    Stores raw payload, then extracts to company_firmographics table.
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
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_payloads")
            .insert({
                "company_domain": request.company_domain,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": request.raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract if firmographics
        extracted_id = None
        if workflow["payload_type"] == "firmographics":
            extracted_id = extract_company_firmographics(
                supabase, raw_id, request.company_domain, request.raw_payload
            )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_find_companies(request: CompanyDiscoveryRequest) -> dict:
    """
    Ingest company discovery payload (clay-find-companies workflow).
    Stores raw payload, then extracts to company_discovery table.
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
            return {"success": False, "error": f"Workflow '{request.workflow_slug}' not found"}

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("company_discovery")
            .insert({
                "company_domain": request.company_domain,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": request.raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract
        extracted_id = extract_find_companies(
            supabase, raw_id, request.company_domain, request.raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
