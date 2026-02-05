"""
Read Router - API wrappers for reading data via Modal serverless functions.
This router provides consistent API endpoints for reading/checking data presence.

Naming convention:
    /read/{entity}/{source}/{action}
"""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Any
from db import get_pool

router = APIRouter(prefix="/read", tags=["read"])

# Modal base URL
MODAL_BASE_URL = "https://bencrane--hq-master-data-ingest"

# =============================================================================
# Request/Response Models
# =============================================================================

class ExistenceCheckRequest(BaseModel):
    domain: str
    schema_name: str
    table_name: str

class ExistenceCheckResponse(BaseModel):
    success: bool
    exists: bool
    domain: str
    schema_name: str
    table_name: str
    error: Optional[str] = None


class ClientLeadsRequest(BaseModel):
    client_domain: str
    limit: Optional[int] = 100
    offset: Optional[int] = 0

class ClientLeadsResponse(BaseModel):
    success: bool
    client_domain: str
    total: int = 0
    leads: List[Any] = []
    error: Optional[str] = None

# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/companies/db/check-existence",
    response_model=ExistenceCheckResponse,
    summary="Check if a company exists in a specific database table",
    description="Wrapper for Modal function: read_db_check_existence"
)
async def read_db_check_existence(request: ExistenceCheckRequest) -> ExistenceCheckResponse:
    """
    Check if a company domain exists in a specific schema and table.

    Modal function: read_db_check_existence
    Modal URL: https://bencrane--hq-master-data-ingest-read-db-check-existence.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-read-db-check-existence.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ExistenceCheckResponse(**response.json())
        except httpx.HTTPStatusError as e:
            # Pass through error details from Modal if available
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text

            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {error_detail}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


@router.post(
    "/client/leads",
    response_model=ClientLeadsResponse,
    summary="Get leads affiliated with a client domain",
    description="Wrapper for Modal function: lookup_client_leads"
)
async def read_client_leads(request: ClientLeadsRequest) -> ClientLeadsResponse:
    """
    Return leads for a client domain, joined with enriched data from core tables.

    Modal function: lookup_client_leads
    Modal URL: https://bencrane--hq-master-data-ingest-lookup-client-leads.modal.run
    """
    modal_url = f"{MODAL_BASE_URL}-lookup-client-leads.modal.run"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                modal_url,
                json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            return ClientLeadsResponse(**response.json())
        except httpx.HTTPStatusError as e:
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text

            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Modal function error: {error_detail}"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to reach Modal function: {str(e)}"
            )


# =============================================================================
# Company Data Coverage Dashboard
# =============================================================================

# All core company tables and the column used for domain lookup
COVERAGE_TABLES = {
    # core.companies base record
    "core.companies": "domain",
    # Dimension tables using "domain"
    "core.company_add_ons_offered": "domain",
    "core.company_annual_commitment_required": "domain",
    "core.company_billing_default": "domain",
    "core.company_business_model": "domain",
    "core.company_categories": "domain",
    "core.company_comparison_pages": "domain",
    "core.company_custom_pricing_mentioned": "domain",
    "core.company_descriptions": "domain",
    "core.company_employee_range": "domain",
    "core.company_employee_ranges": "domain",
    "core.company_enterprise_tier_exists": "domain",
    "core.company_free_trial": "domain",
    "core.company_funding": "domain",
    "core.company_funding_rounds": "domain",
    "core.company_google_ads": "domain",
    "core.company_industries": "domain",
    "core.company_job_postings": "domain",
    "core.company_keywords": "domain",
    "core.company_linkedin_ads": "domain",
    "core.company_locations": "domain",
    "core.company_meta_ads": "domain",
    "core.company_minimum_seats": "domain",
    "core.company_money_back_guarantee": "domain",
    "core.company_naics_codes": "domain",
    "core.company_names": "domain",
    "core.company_number_of_tiers": "domain",
    "core.company_plan_naming_style": "domain",
    "core.company_predictleads_technologies": "domain",
    "core.company_pricing_model": "domain",
    "core.company_pricing_visibility": "domain",
    "core.company_revenue": "domain",
    "core.company_sales_motion": "domain",
    "core.company_security_compliance_gating": "domain",
    "core.company_social_urls": "domain",
    "core.company_tech_on_site": "domain",
    "core.company_types": "domain",
    "core.company_vc_backed": "domain",
    "core.company_webinars": "domain",
    # Tables using "origin_company_domain"
    "core.company_customers": "origin_company_domain",
    # Tables using "company_domain"
    "core.company_people_snapshot_history": "company_domain",
    "core.company_similar_companies_preview": "company_domain",
    "core.company_vc_investments": "company_domain",
    "core.company_vc_investors": "company_domain",
}


@router.get(
    "/companies/coverage",
    summary="Get data coverage for focus companies across all core tables",
    description="Returns boolean flags for each core company table indicating whether data exists for each focus company.",
)
async def get_company_coverage():
    """
    Returns all companies in public.focus_companies with coverage flags
    for every core.company_* table + core.companies.

    Direct asyncpg query — no Modal function.
    """
    pool = get_pool()

    # 1. Get focus companies
    focus_rows = await pool.fetch(
        "SELECT domain, company_name FROM public.focus_companies ORDER BY company_name"
    )
    if not focus_rows:
        return {"success": True, "total": 0, "companies": []}

    domains = [r["domain"] for r in focus_rows]

    # 2. For each table, get the set of domains that exist
    table_domain_sets = {}
    for table_key, domain_col in COVERAGE_TABLES.items():
        schema, table = table_key.split(".", 1)
        rows = await pool.fetch(
            f"SELECT DISTINCT {domain_col} AS d FROM {schema}.{table} WHERE {domain_col} = ANY($1)",
            domains,
        )
        table_domain_sets[table_key] = {r["d"] for r in rows}

    # 3. Assemble response
    companies = []
    for row in focus_rows:
        d = row["domain"]
        coverage = {
            table_key: d in domain_set
            for table_key, domain_set in table_domain_sets.items()
        }
        companies.append({
            "domain": d,
            "company_name": row["company_name"],
            "coverage": coverage,
        })

    return {
        "success": True,
        "total": len(companies),
        "companies": companies,
    }
