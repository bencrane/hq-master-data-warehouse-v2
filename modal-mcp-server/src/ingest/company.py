"""
Company Ingestion Endpoints

- ingest_clay_company_firmo: Enriched company data (clay-company-firmographics)
- ingest_clay_find_companies: Discovery company data (clay-find-companies)
- ingest_all_comp_customers: Customer research from Claygent (claygent-get-all-company-customers)
- upsert_core_company: Direct upsert to core.companies
- ingest_manual_comp_customer: Manual company customer data (manual-company-customers)
- ingest_clay_find_co_lctn_prsd: Discovery company data with pre-parsed location
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# Import app and image from config
from config import app, image

from extraction.company import (
    extract_company_firmographics,
    extract_find_companies,
    extract_company_customers_claygent,
    extract_find_companies_location_parsed,
)


class CompanyIngestRequest(BaseModel):
    company_domain: str
    workflow_slug: str
    raw_payload: dict


class CompanyDiscoveryRequest(BaseModel):
    company_domain: str
    workflow_slug: str
    raw_payload: dict
    clay_table_url: Optional[str] = None


class CompanyDiscoveryLocationParsedRequest(BaseModel):
    company_domain: str
    workflow_slug: str
    raw_company_payload: dict
    raw_company_location_payload: Optional[dict] = None
    clay_table_url: Optional[str] = None


class CompanyCustomerRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: str
    origin_company_linkedin_url: Optional[str] = None
    workflow_slug: str
    raw_payload: dict


class CoreCompanyRequest(BaseModel):
    domain: str
    name: Optional[str] = None
    linkedin_url: Optional[str] = None


class ManualCompanyCustomerRequest(BaseModel):
    origin_company_domain: str
    origin_company_name: Optional[str] = None
    origin_company_linkedin_url: Optional[str] = None
    company_customer_name: str
    company_customer_domain: Optional[str] = None
    company_customer_linkedin_url: Optional[str] = None
    case_study_url: Optional[str] = None
    has_case_study: Optional[bool] = None
    source_notes: Optional[str] = None
    workflow_slug: str


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
                "clay_table_url": request.clay_table_url,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract
        extraction_result = extract_find_companies(
            supabase, raw_id, request.company_domain, request.raw_payload, request.clay_table_url
        )

        # Handle conflict case
        if len(extraction_result) == 4 and extraction_result[1] == "skipped_conflict":
            return {
                "success": False,
                "error": "linkedin_url_conflict",
                "raw_id": raw_id,
                "message": f"Domain {request.company_domain} exists with different linkedin_url. Existing: {extraction_result[2]}, Incoming: {extraction_result[3]}",
            }

        extracted_id, status = extraction_result[0], extraction_result[1]

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "status": status,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_all_comp_customers(request: CompanyCustomerRequest) -> dict:
    """
    Ingest customer research payload from Claygent (claygent-get-all-company-customers workflow).
    Stores raw payload, then extracts company customers to individual rows.
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
            .from_("company_customer_claygent_payloads")
            .insert({
                "origin_company_domain": request.origin_company_domain,
                "origin_company_name": request.origin_company_name,
                "origin_company_linkedin_url": request.origin_company_linkedin_url,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_payload": request.raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract customers (explodes array into individual rows)
        customer_count = extract_company_customers_claygent(
            supabase,
            raw_id,
            request.origin_company_domain,
            request.origin_company_name,
            request.raw_payload
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "customer_count": customer_count,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def upsert_core_company(request: CoreCompanyRequest) -> dict:
    """
    Upsert a company to core.companies.
    Simple direct insert/update on domain.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        data = {
            "domain": request.domain,
            "name": request.name,
            "linkedin_url": request.linkedin_url,
            "updated_at": datetime.utcnow().isoformat(),
        }

        result = (
            supabase.schema("core")
            .from_("companies")
            .upsert(data, on_conflict="domain")
            .execute()
        )

        return {
            "success": True,
            "id": result.data[0]["id"] if result.data else None,
            "domain": request.domain,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_manual_comp_customer(request: ManualCompanyCustomerRequest) -> dict:
    """
    Ingest manually-sourced company customer data (manual-company-customers workflow).
    Data is already flattened, no extraction needed.
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

        # Insert directly to structured table (data is already flattened)
        result = (
            supabase.schema("raw")
            .from_("manual_company_customers")
            .upsert({
                "origin_company_domain": request.origin_company_domain,
                "origin_company_name": request.origin_company_name,
                "origin_company_linkedin_url": request.origin_company_linkedin_url,
                "company_customer_name": request.company_customer_name,
                "company_customer_domain": request.company_customer_domain,
                "company_customer_linkedin_url": request.company_customer_linkedin_url,
                "case_study_url": request.case_study_url,
                "has_case_study": request.has_case_study,
                "source_notes": request.source_notes,
                "updated_at": datetime.utcnow().isoformat(),
            }, on_conflict="origin_company_domain,company_customer_name")
            .execute()
        )

        return {
            "success": True,
            "id": result.data[0]["id"] if result.data else None,
            "origin_company_domain": request.origin_company_domain,
            "company_customer_name": request.company_customer_name,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def ingest_clay_find_co_lctn_prsd(request: CompanyDiscoveryLocationParsedRequest) -> dict:
    """
    Ingest company discovery payload with pre-parsed location.
    Location parsing done in Clay via Gemini before sending to this endpoint.
    Stores raw payload + parsed location, then extracts to company_discovery_location_parsed table.
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
            .from_("company_discovery_location_parsed")
            .insert({
                "company_domain": request.company_domain,
                "workflow_slug": request.workflow_slug,
                "provider": workflow["provider"],
                "platform": workflow["platform"],
                "payload_type": workflow["payload_type"],
                "raw_company_payload": request.raw_company_payload,
                "raw_company_location_payload": request.raw_company_location_payload,
                "clay_table_url": request.clay_table_url,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # Extract with parsed location
        extracted_id = extract_find_companies_location_parsed(
            supabase,
            raw_id,
            request.company_domain,
            request.raw_company_payload,
            request.raw_company_location_payload,
            request.clay_table_url,
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
