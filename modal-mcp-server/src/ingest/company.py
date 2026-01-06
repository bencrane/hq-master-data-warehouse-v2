"""
Company Ingestion Endpoints

- ingest_company_payload: Enriched company data (clay-company-firmographics)
- ingest_company_discovery: Discovery company data (clay-find-companies)
"""

import os
import modal

from config import app, image


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_payload(request: dict) -> dict:
    """
    Ingest enriched company payload (clay-company-firmographics workflow).
    Stores raw payload, then extracts to company_firmographics table.
    """
    from supabase import create_client
    from extraction.company import extract_company_firmographics

    company_domain = request.get("company_domain")
    workflow_slug = request.get("workflow_slug")
    raw_payload = request.get("raw_payload")

    if not company_domain or not workflow_slug or not raw_payload:
        return {"success": False, "error": "Missing required fields: company_domain, workflow_slug, raw_payload"}

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{workflow_slug}' not found"}

        raw_insert = (
            supabase.schema("raw")
            .from_("company_payloads")
            .insert({
                "company_domain": company_domain,
                "workflow_slug": workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        extracted_id = None
        if workflow["payload_type"] == "firmographics":
            extracted_id = extract_company_firmographics(
                supabase, raw_id, company_domain, raw_payload
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
def ingest_company_discovery(request: dict) -> dict:
    """
    Ingest company discovery payload (clay-find-companies workflow).
    Stores raw payload, then extracts to company_discovery table.
    """
    from supabase import create_client
    from extraction.company import extract_company_discovery

    company_domain = request.get("company_domain")
    workflow_slug = request.get("workflow_slug")
    raw_payload = request.get("raw_payload")

    if not company_domain or not workflow_slug or not raw_payload:
        return {"success": False, "error": "Missing required fields: company_domain, workflow_slug, raw_payload"}

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        workflow_result = (
            supabase.schema("reference")
            .from_("enrichment_workflow_registry")
            .select("*")
            .eq("workflow_slug", workflow_slug)
            .single()
            .execute()
        )
        workflow = workflow_result.data

        if not workflow:
            return {"success": False, "error": f"Workflow '{workflow_slug}' not found"}

        raw_insert = (
            supabase.schema("raw")
            .from_("company_discovery")
            .insert({
                "company_domain": company_domain,
                "workflow_slug": workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        extracted_id = extract_company_discovery(
            supabase, raw_id, company_domain, raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
