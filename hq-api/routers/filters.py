from fastapi import APIRouter
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
