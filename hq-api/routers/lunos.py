"""
Lunos Router - API endpoints for Lunos target companies and contacts.
"""

from fastapi import APIRouter
from typing import List, Any, Optional
from db import get_pool

router = APIRouter(prefix="/read/lunos", tags=["lunos"])


@router.get(
    "/targets",
    summary="Get all Lunos target companies with their contacts",
    description="Returns companies joined with contacts on domain. Only companies with contacts are included.",
)
async def get_lunos_targets():
    """
    Get all Lunos target companies with their associated contacts.

    Returns companies from lunos_targets joined with lunos_target_contacts on domain.
    Only companies that have at least one contact are returned (INNER JOIN).

    Frontend handles filtering and sorting.
    """
    pool = get_pool()

    rows = await pool.fetch(
        """
        SELECT
            -- Company fields (prefixed with company_)
            t.id AS company_id,
            t.name AS company_name,
            t.description AS company_description,
            t.primary_industry,
            t.size AS company_size,
            t.type AS company_type,
            t.location AS company_location,
            t.country AS company_country,
            t.domain,
            t.linkedin_url AS company_linkedin_url,
            t.annual_estimated_revenue,
            t.total_sales_hires,
            t.total_finance_hires,
            t.sales_hires_within_6_months,
            t.finance_hires_within_6_months,
            t.created_at AS company_created_at,
            t.updated_at AS company_updated_at,
            -- Contact fields (prefixed with contact_)
            c.id AS contact_id,
            c.first_name AS contact_first_name,
            c.last_name AS contact_last_name,
            c.full_name AS contact_full_name,
            c.raw_job_title AS contact_raw_job_title,
            c.normalized_job_title AS contact_normalized_job_title,
            c.location AS contact_location,
            c.person_linkedin_url AS contact_linkedin_url,
            c.created_at AS contact_created_at,
            c.updated_at AS contact_updated_at
        FROM public.lunos_targets t
        INNER JOIN public.lunos_target_contacts c ON t.domain = c.domain
        ORDER BY t.name, c.full_name
        """
    )

    return {
        "success": True,
        "total": len(rows),
        "data": [dict(r) for r in rows],
    }
