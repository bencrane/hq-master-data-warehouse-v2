from fastapi import APIRouter, Query
from typing import Optional, List
from pydantic import BaseModel
from db import supabase


router = APIRouter(prefix="/api/filters", tags=["filters"])


class FilterOption(BaseModel):
    name: str
    sort_order: int = 0


class EmployeeRangeOption(BaseModel):
    name: str
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    sort_order: int = 0


class SignalOption(BaseModel):
    name: str
    display_name: str
    endpoint: Optional[str] = None
    sort_order: int = 0


class IndustryOption(BaseModel):
    name: str


class AllFiltersResponse(BaseModel):
    seniorities: List[FilterOption]
    job_functions: List[FilterOption]
    employee_ranges: List[EmployeeRangeOption]
    industries: List[IndustryOption]
    signals: List[SignalOption]
    business_models: List[FilterOption]


def reference():
    """Get reference schema client."""
    return supabase.schema("reference")


@router.get("", response_model=AllFiltersResponse)
async def get_all_filters():
    """
    Get all filter options from reference tables.

    This is the canonical source of truth for frontend dropdowns.
    All values come from reference tables, not from querying data.
    """
    # Seniorities
    seniorities_result = (
        reference()
        .from_("seniorities")
        .select("name, sort_order")
        .order("sort_order")
        .execute()
    )

    # Job Functions
    job_functions_result = (
        reference()
        .from_("job_functions")
        .select("name, sort_order")
        .order("sort_order")
        .execute()
    )

    # Employee Ranges
    employee_ranges_result = (
        reference()
        .from_("employee_ranges")
        .select("name, min_employees, max_employees, sort_order")
        .order("sort_order")
        .execute()
    )

    # Industries (from company_industries)
    industries_result = (
        reference()
        .from_("company_industries")
        .select("name")
        .order("name")
        .execute()
    )

    # Signals
    signals_result = (
        reference()
        .from_("signals")
        .select("name, display_name, endpoint, sort_order")
        .order("sort_order")
        .execute()
    )

    # Business Models
    business_models_result = (
        reference()
        .from_("business_models")
        .select("name, sort_order")
        .order("sort_order")
        .execute()
    )

    return AllFiltersResponse(
        seniorities=[FilterOption(**row) for row in seniorities_result.data],
        job_functions=[FilterOption(**row) for row in job_functions_result.data],
        employee_ranges=[EmployeeRangeOption(**row) for row in employee_ranges_result.data],
        industries=[IndustryOption(**row) for row in industries_result.data],
        signals=[SignalOption(**row) for row in signals_result.data],
        business_models=[FilterOption(**row) for row in business_models_result.data],
    )


@router.get("/seniorities", response_model=List[FilterOption])
async def get_seniorities():
    """Get seniority levels from reference table."""
    result = reference().from_("seniorities").select("name, sort_order").order("sort_order").execute()
    return [FilterOption(**row) for row in result.data]


@router.get("/job-functions", response_model=List[FilterOption])
async def get_job_functions():
    """Get job functions from reference table."""
    result = reference().from_("job_functions").select("name, sort_order").order("sort_order").execute()
    return [FilterOption(**row) for row in result.data]


@router.get("/employee-ranges", response_model=List[EmployeeRangeOption])
async def get_employee_ranges():
    """Get employee ranges from reference table."""
    result = reference().from_("employee_ranges").select("name, min_employees, max_employees, sort_order").order("sort_order").execute()
    return [EmployeeRangeOption(**row) for row in result.data]


@router.get("/industries", response_model=List[IndustryOption])
async def get_industries():
    """Get industries from reference table."""
    result = reference().from_("company_industries").select("name").order("name").execute()
    return [IndustryOption(**row) for row in result.data]


@router.get("/signals", response_model=List[SignalOption])
async def get_signals():
    """Get signals from reference table."""
    result = reference().from_("signals").select("name, display_name, endpoint, sort_order").order("sort_order").execute()
    return [SignalOption(**row) for row in result.data]


@router.get("/business-models", response_model=List[FilterOption])
async def get_business_models():
    """Get business models from reference table."""
    result = reference().from_("business_models").select("name, sort_order").order("sort_order").execute()
    return [FilterOption(**row) for row in result.data]


@router.get("/countries", response_model=List[dict])
async def get_countries():
    """Get countries from reference table."""
    result = reference().from_("countries").select("name, code").order("name").execute()
    return result.data
