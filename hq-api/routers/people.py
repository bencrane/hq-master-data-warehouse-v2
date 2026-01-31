from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date
from db import core
from models import Person, PeopleResponse, PaginationMeta

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
