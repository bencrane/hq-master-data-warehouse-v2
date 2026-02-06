from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date
from db import core, get_pool
from models import Person, PeopleResponse, PaginationMeta, WorkHistoryEntry, PersonWorkHistoryResponse, PersonEnrichmentStatusResponse, LinkedInUrlRequest

router = APIRouter(prefix="/api/people", tags=["people"])

PERSON_COLUMNS = ",".join([
    "id", "linkedin_url", "linkedin_slug", "full_name", "core_company_id",
    "linkedin_url_type", "linkedin_user_profile_urn",
    "person_city", "person_state", "person_country",
    "matched_cleaned_job_title", "matched_job_function", "matched_seniority",
    "job_start_date", "created_at", "updated_at"
])


def apply_person_filters(query, params: dict):
    """Apply filters to a people query."""
    if params.get("job_function"):
        functions = params["job_function"].split(",")
        query = query.in_("matched_job_function", functions)
    if params.get("seniority"):
        seniorities = params["seniority"].split(",")
        query = query.in_("matched_seniority", seniorities)
    if params.get("person_city"):
        query = query.ilike("person_city", f"%{params['person_city']}%")
    if params.get("person_state"):
        query = query.ilike("person_state", f"%{params['person_state']}%")
    if params.get("person_country"):
        query = query.ilike("person_country", f"%{params['person_country']}%")
    if params.get("job_title"):
        query = query.ilike("matched_cleaned_job_title", f"%{params['job_title']}%")
    if params.get("full_name"):
        query = query.ilike("full_name", f"%{params['full_name']}%")
    if params.get("linkedin_url"):
        query = query.eq("linkedin_url", params["linkedin_url"])
    if params.get("job_start_date_gte"):
        query = query.gte("job_start_date", params["job_start_date_gte"])
    if params.get("job_start_date_lte"):
        query = query.lte("job_start_date", params["job_start_date_lte"])
    return query


@router.get("", response_model=PeopleResponse)
async def get_people(
    job_function: Optional[str] = Query(None, description="Filter by job function (comma-separated)"),
    seniority: Optional[str] = Query(None, description="Filter by seniority (comma-separated)"),
    person_city: Optional[str] = Query(None),
    person_state: Optional[str] = Query(None),
    person_country: Optional[str] = Query(None),
    job_title: Optional[str] = Query(None),
    full_name: Optional[str] = Query(None),
    linkedin_url: Optional[str] = Query(None, description="Exact match on LinkedIn URL"),
    job_start_date_gte: Optional[date] = Query(None),
    job_start_date_lte: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get people with optional filters."""
    try:
        params = {
            "job_function": job_function,
            "seniority": seniority,
            "person_city": person_city,
            "person_state": person_state,
            "person_country": person_country,
            "job_title": job_title,
            "full_name": full_name,
            "linkedin_url": linkedin_url,
            "job_start_date_gte": str(job_start_date_gte) if job_start_date_gte else None,
            "job_start_date_lte": str(job_start_date_lte) if job_start_date_lte else None,
        }

        # Count query
        count_query = core().from_("people_full").select("id", count="exact", head=True)
        count_query = apply_person_filters(count_query, params)
        count_result = count_query.execute()
        total = count_result.count or 0

        # Data query
        data_query = core().from_("people_full").select(PERSON_COLUMNS)
        data_query = apply_person_filters(data_query, params)
        data_query = data_query.range(offset, offset + limit - 1)
        data_result = data_query.execute()

        return PeopleResponse(
            data=[Person(**row) for row in data_result.data],
            meta=PaginationMeta(total=total, limit=limit, offset=offset)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("/work-history", response_model=PersonWorkHistoryResponse)
async def get_person_work_history(body: LinkedInUrlRequest):
    """
    Get a person's full work history from enrichment data.
    Returns all past and current positions.
    """
    pool = get_pool()

    rows = await pool.fetch("""
        SELECT
            company_name, company_domain, company_linkedin_url,
            title, matched_job_function, matched_seniority,
            start_date, end_date, is_current, created_at
        FROM core.person_work_history
        WHERE linkedin_url = $1
        ORDER BY is_current DESC, start_date DESC NULLS LAST
    """, body.linkedin_url)

    work_history = [
        WorkHistoryEntry(
            company_name=row["company_name"],
            company_domain=row["company_domain"],
            company_linkedin_url=row["company_linkedin_url"],
            title=row["title"],
            matched_job_function=row["matched_job_function"],
            matched_seniority=row["matched_seniority"],
            start_date=row["start_date"],
            end_date=row["end_date"],
            is_current=row["is_current"],
            created_at=row["created_at"]
        )
        for row in rows
    ]

    return PersonWorkHistoryResponse(
        linkedin_url=body.linkedin_url,
        has_work_history=len(work_history) > 0,
        entry_count=len(work_history),
        work_history=work_history
    )


@router.post("/enrichment-status", response_model=PersonEnrichmentStatusResponse)
async def get_person_enrichment_status(body: LinkedInUrlRequest):
    """
    Quick check if a person has been enriched (has work history data).
    Returns enrichment status and the date of last insert.
    """
    pool = get_pool()

    row = await pool.fetchrow("""
        SELECT
            COUNT(*) as entry_count,
            MAX(created_at) as last_enriched_at
        FROM core.person_work_history
        WHERE linkedin_url = $1
    """, body.linkedin_url)

    entry_count = row["entry_count"] if row else 0
    last_enriched_at = row["last_enriched_at"] if row else None

    return PersonEnrichmentStatusResponse(
        linkedin_url=body.linkedin_url,
        is_enriched=entry_count > 0,
        entry_count=entry_count,
        last_enriched_at=str(last_enriched_at) if last_enriched_at else None
    )


@router.post("/workflow-enrichment-status")
async def check_person_workflow_enrichment_status(payload: dict):
    """
    Check if a person has been enriched by a specific workflow.

    Payload: {
        "company_name": "Acme Inc",           # optional (for clarity)
        "domain": "acme.com",                 # optional (for clarity)
        "person_linkedin_url": "linkedin.com/in/johndoe",  # required
        "workflow_slug": "clay-person-profile"  # required
    }

    Returns: { "enriched": true/false, "last_enriched_at": timestamp }
    """
    from db import reference

    person_linkedin_url = payload.get("person_linkedin_url", "").strip()
    workflow_slug = payload.get("workflow_slug", "").strip()

    if not person_linkedin_url:
        return {"error": "person_linkedin_url is required", "enriched": False}
    if not workflow_slug:
        return {"error": "workflow_slug is required", "enriched": False}

    # Look up core_table from registry
    registry_result = (
        reference()
        .from_("enrichment_workflow_registry")
        .select("core_table")
        .eq("workflow_slug", workflow_slug)
        .limit(1)
        .execute()
    )

    if not registry_result.data:
        return {
            "error": f"workflow_slug '{workflow_slug}' not found in registry",
            "enriched": False
        }

    core_table = registry_result.data[0].get("core_table")

    if not core_table:
        return {
            "error": f"workflow '{workflow_slug}' has no core_table mapped",
            "enriched": False,
            "note": "This workflow may not write to core schema"
        }

    # Query the core table for this person
    pool = get_pool()

    # Parse schema and table name
    if "." in core_table:
        schema, table = core_table.split(".", 1)
    else:
        schema, table = "core", core_table

    row = await pool.fetchrow(f"""
        SELECT COUNT(*) as count, MAX(created_at) as last_enriched_at
        FROM {schema}.{table}
        WHERE linkedin_url = $1
    """, person_linkedin_url)

    count = row["count"] if row else 0
    last_enriched_at = row["last_enriched_at"] if row else None

    return {
        "person_linkedin_url": person_linkedin_url,
        "workflow_slug": workflow_slug,
        "core_table": core_table,
        "enriched": count > 0,
        "count": count,
        "last_enriched_at": str(last_enriched_at) if last_enriched_at else None
    }
