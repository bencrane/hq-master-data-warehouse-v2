"""
Upsert ICP Criteria Endpoint

Upserts ICP filter criteria for a company to core.icp_criteria.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class UpsertICPCriteriaRequest(BaseModel):
    """Request model for upserting ICP criteria."""
    domain: str
    company_name: Optional[str] = None

    # Company filters
    industries: Optional[list[str]] = None
    countries: Optional[list[str]] = None
    employee_ranges: Optional[list[str]] = None
    funding_stages: Optional[list[str]] = None

    # People filters
    job_titles: Optional[list[str]] = None
    seniorities: Optional[list[str]] = None
    job_functions: Optional[list[str]] = None

    # Value prop
    value_proposition: Optional[str] = None
    core_benefit: Optional[str] = None
    target_customer: Optional[str] = None
    key_differentiator: Optional[str] = None


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
)
@modal.fastapi_endpoint(method="POST")
def upsert_icp_criteria(request: UpsertICPCriteriaRequest) -> dict:
    """
    Upsert ICP criteria for a company.
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        record = {
            "domain": request.domain,
            "company_name": request.company_name,
            "industries": request.industries,
            "countries": request.countries,
            "employee_ranges": request.employee_ranges,
            "funding_stages": request.funding_stages,
            "job_titles": request.job_titles,
            "seniorities": request.seniorities,
            "job_functions": request.job_functions,
            "value_proposition": request.value_proposition,
            "core_benefit": request.core_benefit,
            "target_customer": request.target_customer,
            "key_differentiator": request.key_differentiator,
        }

        # Remove None values so they don't overwrite existing data
        record = {k: v for k, v in record.items() if v is not None}
        record["domain"] = request.domain  # Always include domain

        result = (
            supabase.schema("core")
            .from_("icp_criteria")
            .upsert(record, on_conflict="domain")
            .execute()
        )

        return {
            "success": True,
            "domain": request.domain,
            "id": result.data[0]["id"] if result.data else None,
        }

    except Exception as e:
        import traceback
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}
