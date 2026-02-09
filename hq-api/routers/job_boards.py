"""
Job Boards API endpoints.

Serves job postings for white-label job board domains.
Each domain maps to specific job function(s) via reference.job_board_domains.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import json
from db import get_pool

router = APIRouter(prefix="/job-boards", tags=["job-boards"])


@router.get("/jobs/{domain}")
async def get_jobs_for_domain(
    domain: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    days_ago: Optional[int] = Query(None),
):
    """
    Get job postings for a job board domain with company enrichment.
    """
    pool = get_pool()

    domain_lower = domain.lower().strip()
    config = await pool.fetchrow("""
        SELECT job_functions, display_name, is_active
        FROM reference.job_board_domains
        WHERE domain = $1
    """, domain_lower)

    if not config:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not configured")

    if not config['is_active']:
        raise HTTPException(status_code=403, detail=f"Domain '{domain}' is not active")

    # Handle JSONB - asyncpg may return string or parsed object
    job_functions = config['job_functions']
    if isinstance(job_functions, str):
        job_functions = json.loads(job_functions)

    query = """
        SELECT
            jp.id,
            jp.domain as company_domain,
            jp.title,
            jp.job_function,
            jp.url,
            jp.location,
            jp.city,
            jp.state,
            jp.country,
            jp.seniority,
            jp.employment_type,
            jp.salary_min,
            jp.salary_max,
            jp.salary_currency,
            jp.posted_at,
            jp.created_at,
            cd.description as company_description,
            cd.tagline as company_tagline,
            cr.raw_revenue_amount as company_revenue,
            cr.raw_revenue_range as company_revenue_range,
            cf.raw_funding_amount as company_funding,
            cf.raw_funding_range as company_funding_range,
            ce.employee_range as company_employee_range
        FROM core.company_job_postings jp
        LEFT JOIN core.company_descriptions cd ON jp.domain = cd.domain
        LEFT JOIN core.company_revenue cr ON jp.domain = cr.domain
        LEFT JOIN core.company_funding cf ON jp.domain = cf.domain
        LEFT JOIN core.company_employee_range ce ON jp.domain = ce.domain
        WHERE jp.job_function = ANY($1::text[])
    """

    params = [job_functions]
    param_idx = 2

    if city:
        query += f" AND jp.city ILIKE ${param_idx}"
        params.append(f"%{city}%")
        param_idx += 1

    if state:
        query += f" AND jp.state ILIKE ${param_idx}"
        params.append(f"%{state}%")
        param_idx += 1

    if country:
        query += f" AND jp.country ILIKE ${param_idx}"
        params.append(f"%{country}%")
        param_idx += 1

    if days_ago:
        query += f" AND jp.posted_at >= NOW() - INTERVAL '{days_ago} days'"

    query += f" ORDER BY jp.posted_at DESC NULLS LAST, jp.created_at DESC"
    query += f" LIMIT ${param_idx} OFFSET ${param_idx + 1}"
    params.extend([limit, offset])

    jobs = await pool.fetch(query, *params)

    # Get total count
    count_query = """
        SELECT COUNT(*) FROM core.company_job_postings jp
        WHERE jp.job_function = ANY($1::text[])
    """
    count_params = [job_functions]
    param_idx = 2

    if city:
        count_query += f" AND jp.city ILIKE ${param_idx}"
        count_params.append(f"%{city}%")
        param_idx += 1
    if state:
        count_query += f" AND jp.state ILIKE ${param_idx}"
        count_params.append(f"%{state}%")
        param_idx += 1
    if country:
        count_query += f" AND jp.country ILIKE ${param_idx}"
        count_params.append(f"%{country}%")
        param_idx += 1
    if days_ago:
        count_query += f" AND jp.posted_at >= NOW() - INTERVAL '{days_ago} days'"

    total = await pool.fetchval(count_query, *count_params)

    return {
        "domain": domain_lower,
        "display_name": config['display_name'],
        "job_functions": job_functions,
        "jobs": [dict(job) for job in jobs],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total
        }
    }


@router.get("/jobs/{domain}/stats")
async def get_stats_for_domain(domain: str):
    """
    Get job posting statistics for a job board domain.
    """
    pool = get_pool()

    domain_lower = domain.lower().strip()
    config = await pool.fetchrow("""
        SELECT job_functions, display_name, is_active
        FROM reference.job_board_domains
        WHERE domain = $1
    """, domain_lower)

    if not config:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' not configured")

    job_functions = config['job_functions']
    if isinstance(job_functions, str):
        job_functions = json.loads(job_functions)

    stats = await pool.fetchrow("""
        SELECT
            COUNT(*) as total_jobs,
            COUNT(DISTINCT jp.domain) as unique_companies,
            COUNT(CASE WHEN jp.posted_at >= NOW() - INTERVAL '7 days' THEN 1 END) as jobs_last_7_days,
            COUNT(CASE WHEN jp.posted_at >= NOW() - INTERVAL '30 days' THEN 1 END) as jobs_last_30_days
        FROM core.company_job_postings jp
        WHERE jp.job_function = ANY($1::text[])
    """, job_functions)

    top_locations = await pool.fetch("""
        SELECT COALESCE(city, state, country, 'Unknown') as location, COUNT(*) as count
        FROM core.company_job_postings
        WHERE job_function = ANY($1::text[])
        GROUP BY COALESCE(city, state, country, 'Unknown')
        ORDER BY count DESC
        LIMIT 10
    """, job_functions)

    top_companies = await pool.fetch("""
        SELECT jp.domain, COUNT(*) as job_count, cd.description as company_description
        FROM core.company_job_postings jp
        LEFT JOIN core.company_descriptions cd ON jp.domain = cd.domain
        WHERE jp.job_function = ANY($1::text[])
        GROUP BY jp.domain, cd.description
        ORDER BY job_count DESC
        LIMIT 10
    """, job_functions)

    return {
        "domain": domain_lower,
        "display_name": config['display_name'],
        "job_functions": job_functions,
        "stats": dict(stats),
        "top_locations": [dict(loc) for loc in top_locations],
        "top_companies": [dict(co) for co in top_companies]
    }


@router.get("/domains")
async def list_job_board_domains(active_only: bool = Query(True)):
    """
    List all configured job board domains.
    """
    pool = get_pool()

    query = """
        SELECT domain, job_functions, display_name, description, is_active, created_at
        FROM reference.job_board_domains
    """
    if active_only:
        query += " WHERE is_active = true"
    query += " ORDER BY domain"

    domains = await pool.fetch(query)

    return {
        "domains": [dict(d) for d in domains],
        "total": len(domains)
    }
