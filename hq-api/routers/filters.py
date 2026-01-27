from fastapi import APIRouter, Query
from typing import Optional
from db import core, raw
from models import FiltersResponse, FilterOption

router = APIRouter(prefix="/api/filters", tags=["filters"])


@router.get("/job-functions", response_model=FiltersResponse)
async def get_job_functions():
    """Get all available job functions for filter dropdowns."""
    result = core().from_("leads").select("matched_job_function").not_.is_("matched_job_function", "null").limit(10000).execute()
    values = list(set([row["matched_job_function"] for row in result.data if row["matched_job_function"]]))
    return FiltersResponse(data=[FilterOption(value=v, count=0) for v in sorted(values)])


@router.get("/seniorities", response_model=FiltersResponse)
async def get_seniorities():
    """Get all available seniority levels for filter dropdowns."""
    result = core().from_("leads").select("matched_seniority").not_.is_("matched_seniority", "null").limit(10000).execute()
    values = list(set([row["matched_seniority"] for row in result.data if row["matched_seniority"]]))
    return FiltersResponse(data=[FilterOption(value=v, count=0) for v in sorted(values)])


@router.get("/industries", response_model=FiltersResponse)
async def get_industries():
    """Get all available industries for filter dropdowns."""
    result = core().from_("leads").select("matched_industry").not_.is_("matched_industry", "null").limit(10000).execute()
    values = list(set([row["matched_industry"] for row in result.data if row["matched_industry"]]))
    return FiltersResponse(data=[FilterOption(value=v, count=0) for v in sorted(values)])


@router.get("/employee-ranges", response_model=FiltersResponse)
async def get_employee_ranges():
    """Get all available employee ranges for filter dropdowns."""
    result = core().from_("leads").select("employee_range").not_.is_("employee_range", "null").limit(10000).execute()
    values = list(set([row["employee_range"] for row in result.data if row["employee_range"]]))

    # Sort by numeric order
    def sort_key(v):
        try:
            return int(v.split("-")[0].replace(",", "").replace("+", ""))
        except:
            return 999999

    return FiltersResponse(data=[FilterOption(value=v, count=0) for v in sorted(values, key=sort_key)])


@router.get("/vc-firms", response_model=FiltersResponse)
async def get_vc_firms():
    """Get all available VC firm names for filter dropdowns."""
    result = raw().from_("vc_firms").select("name").order("name").execute()
    return FiltersResponse(data=[FilterOption(value=row["name"], count=0) for row in result.data])


@router.get("/person-countries", response_model=FiltersResponse)
async def get_person_countries():
    """Get all available person countries for filter dropdowns."""
    result = core().from_("leads").select("person_country").not_.is_("person_country", "null").limit(10000).execute()
    values = list(set([row["person_country"] for row in result.data if row["person_country"]]))
    return FiltersResponse(data=[FilterOption(value=v, count=0) for v in sorted(values)])


@router.get("/person-states", response_model=FiltersResponse)
async def get_person_states():
    """Get all available person states for filter dropdowns."""
    result = core().from_("leads").select("person_state").not_.is_("person_state", "null").limit(10000).execute()
    values = list(set([row["person_state"] for row in result.data if row["person_state"]]))
    return FiltersResponse(data=[FilterOption(value=v, count=0) for v in sorted(values)])


@router.get("/job-titles", response_model=FiltersResponse)
async def get_job_titles(
    q: Optional[str] = Query(None, description="Search query for job title autocomplete"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Search job titles for autocomplete.

    Pass `q` param to search (e.g., ?q=VP returns "VP of Sales", "VP Marketing", etc.)
    Without `q`, returns top job titles by frequency.
    """
    if q and len(q) >= 2:
        # Search with ilike
        result = (
            core()
            .from_("leads")
            .select("matched_cleaned_job_title")
            .ilike("matched_cleaned_job_title", f"%{q}%")
            .not_.is_("matched_cleaned_job_title", "null")
            .limit(5000)
            .execute()
        )
    else:
        # Return all (limited)
        result = (
            core()
            .from_("leads")
            .select("matched_cleaned_job_title")
            .not_.is_("matched_cleaned_job_title", "null")
            .limit(5000)
            .execute()
        )

    # Count occurrences and dedupe
    title_counts = {}
    for row in result.data:
        title = row["matched_cleaned_job_title"]
        if title:
            title_counts[title] = title_counts.get(title, 0) + 1

    # Sort by count (most common first), then alphabetically
    sorted_titles = sorted(title_counts.items(), key=lambda x: (-x[1], x[0]))[:limit]

    return FiltersResponse(
        data=[FilterOption(value=title, count=count) for title, count in sorted_titles]
    )
