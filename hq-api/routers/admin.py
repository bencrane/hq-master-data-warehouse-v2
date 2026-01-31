from fastapi import APIRouter, Query, HTTPException, Path
from typing import Optional, List, Any, Literal
from pydantic import BaseModel
from db import get_pool

router = APIRouter(prefix="/api/admin", tags=["admin"])


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class TableCountResponse(BaseModel):
    schema_name: str
    table_name: str
    count: int


class TableDataResponse(BaseModel):
    schema_name: str
    table_name: str
    data: List[dict]
    meta: PaginationMeta


# ============================================================
# Gap Analysis Recipes
# ============================================================

class GapRecipe(BaseModel):
    id: str
    label: str
    description: str
    source_table: str
    target_table: str
    join_column: str
    comparison: Literal["not_in_target", "in_target"]
    priority: Literal["P0", "P1", "P2", "P3"]
    # Optional: how to join for country filtering. Format: "location_table:join_col:country_col"
    # e.g., "core.company_locations:domain:country" means JOIN core.company_locations ON domain, filter by country
    country_join: Optional[str] = None


class GapRecipeListResponse(BaseModel):
    recipes: List[GapRecipe]


class GapCountResponse(BaseModel):
    recipe_id: str
    label: str
    count: int
    source_table: str
    target_table: str


class GapSampleResponse(BaseModel):
    recipe_id: str
    label: str
    count: int
    sample: List[dict]
    limit: int


# Define all gap recipes
GAP_RECIPES: List[GapRecipe] = [
    # P0 - Pipeline health: extraction to core
    GapRecipe(
        id="extracted-companies-not-in-core",
        label="Companies stuck in extraction",
        description="Companies in extracted.company_discovery that haven't made it to core.companies. These may have data quality issues preventing promotion to core.",
        source_table="extracted.company_discovery",
        target_table="core.companies",
        join_column="domain",
        comparison="not_in_target",
        priority="P0"
    ),
    GapRecipe(
        id="extracted-people-not-in-core",
        label="People stuck in extraction",
        description="People in extracted.person_discovery that haven't made it to core.people. These may be missing required fields or have invalid LinkedIn URLs.",
        source_table="extracted.person_discovery",
        target_table="core.people",
        join_column="linkedin_url",
        comparison="not_in_target",
        priority="P0"
    ),
    # P1 - Data quality: core records missing enrichment
    GapRecipe(
        id="companies-missing-industry",
        label="Companies missing industry",
        description="Companies in core.companies that don't have an industry classification in core.company_industries.",
        source_table="core.companies",
        target_table="core.company_industries",
        join_column="domain",
        comparison="not_in_target",
        priority="P1"
    ),
    GapRecipe(
        id="companies-missing-location",
        label="Companies missing location",
        description="Companies in core.companies that don't have location data in core.company_locations.",
        source_table="core.companies",
        target_table="core.company_locations",
        join_column="domain",
        comparison="not_in_target",
        priority="P1"
    ),
    GapRecipe(
        id="people-missing-job-title",
        label="People missing job title",
        description="People in core.people that don't have job title data in core.person_job_titles.",
        source_table="core.people",
        target_table="core.person_job_titles",
        join_column="linkedin_url",
        comparison="not_in_target",
        priority="P1"
    ),
    GapRecipe(
        id="people-missing-location",
        label="People missing location",
        description="People in core.people that don't have location data in core.person_locations.",
        source_table="core.people",
        target_table="core.person_locations",
        join_column="linkedin_url",
        comparison="not_in_target",
        priority="P1"
    ),
    # P2 - Additional data quality gaps
    GapRecipe(
        id="companies-missing-description",
        label="Companies missing description",
        description="Companies in core.companies that don't have a description in core.company_descriptions.",
        source_table="core.companies",
        target_table="core.company_descriptions",
        join_column="domain",
        comparison="not_in_target",
        priority="P2"
    ),
    GapRecipe(
        id="companies-missing-employee-range",
        label="Companies missing employee range",
        description="Companies in core.companies that don't have employee range data in core.company_employee_range.",
        source_table="core.companies",
        target_table="core.company_employee_range",
        join_column="domain",
        comparison="not_in_target",
        priority="P2"
    ),
    GapRecipe(
        id="people-missing-tenure",
        label="People missing tenure",
        description="People in core.people that don't have job start date/tenure data in core.person_tenure.",
        source_table="core.people",
        target_table="core.person_tenure",
        join_column="linkedin_url",
        comparison="not_in_target",
        priority="P2"
    ),
    GapRecipe(
        id="customers-without-find-similar",
        label="Customer companies not enriched with find-similar",
        description="Unique customer domains from core.company_customers that haven't had find-similar-companies run on them yet.",
        source_table="core.company_customers",
        target_table="extracted.company_enrich_similar",
        join_column="customer_domain:input_domain",  # Special syntax: source_col:target_col
        comparison="not_in_target",
        priority="P2"
    ),
    # P3 - VC-backed companies gaps
    GapRecipe(
        id="vc-backed-without-customers",
        label="VC-backed companies without customers",
        description="Companies that have raised VC funding but we haven't yet identified their customers.",
        source_table="core.company_vc_backed",
        target_table="core.company_customers",
        join_column="domain:origin_company_domain",
        comparison="not_in_target",
        priority="P3",
        country_join="core.company_locations:domain:country"
    ),
]

# Index recipes by ID for fast lookup
RECIPES_BY_ID = {r.id: r for r in GAP_RECIPES}


def parse_join_columns(join_column: str) -> tuple[str, str]:
    """Parse join_column which may be 'col' or 'source_col:target_col'."""
    if ":" in join_column:
        source_col, target_col = join_column.split(":")
        return source_col, target_col
    return join_column, join_column


def build_country_filter(country_join: Optional[str], country: Optional[str], source_col: str) -> tuple[str, str]:
    """
    Build JOIN and WHERE clauses for country filtering.

    country_join format: "location_table:join_col:country_col"
    country values: None (no filter), "United States", "not United States"

    Returns: (join_clause, where_clause)
    """
    if not country_join or not country:
        return "", ""

    parts = country_join.split(":")
    if len(parts) != 3:
        return "", ""

    location_table, join_col, country_col = parts

    join_clause = f"INNER JOIN {location_table} loc ON loc.{join_col} = s.{source_col}"

    if country == "United States":
        where_clause = f"AND loc.{country_col} = 'United States'"
    elif country == "not United States":
        where_clause = f"AND loc.{country_col} != 'United States' AND loc.{country_col} IS NOT NULL"
    else:
        where_clause = ""

    return join_clause, where_clause


@router.get("/gaps/recipes", response_model=GapRecipeListResponse, tags=["gaps"])
async def get_gap_recipes():
    """Get all available gap analysis recipes."""
    return GapRecipeListResponse(recipes=GAP_RECIPES)


@router.get("/gaps/recipes/{recipe_id}/count", response_model=GapCountResponse, tags=["gaps"])
async def get_gap_recipe_count(
    recipe_id: str = Path(..., description="The recipe ID"),
    country: Optional[str] = Query(None, description="Filter by country: 'United States', 'not United States', or omit for all")
):
    """Get the count of records matching a gap recipe, optionally filtered by country."""
    if recipe_id not in RECIPES_BY_ID:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")

    recipe = RECIPES_BY_ID[recipe_id]
    pool = get_pool()

    # Parse join columns (handles both 'col' and 'source_col:target_col' formats)
    source_col, target_col = parse_join_columns(recipe.join_column)

    # Build country filter if applicable
    country_join_clause, country_where_clause = build_country_filter(
        recipe.country_join, country, source_col
    )

    if recipe.comparison == "not_in_target":
        query = f"""
            SELECT COUNT(*) FROM {recipe.source_table} s
            {country_join_clause}
            WHERE s.{source_col} IS NOT NULL
            AND s.{source_col} != ''
            {country_where_clause}
            AND NOT EXISTS (
                SELECT 1 FROM {recipe.target_table} t
                WHERE t.{target_col} = s.{source_col}
            )
        """
    else:  # in_target
        query = f"""
            SELECT COUNT(*) FROM {recipe.source_table} s
            {country_join_clause}
            WHERE s.{source_col} IS NOT NULL
            AND s.{source_col} != ''
            {country_where_clause}
            AND EXISTS (
                SELECT 1 FROM {recipe.target_table} t
                WHERE t.{target_col} = s.{source_col}
            )
        """

    count = await pool.fetchval(query)

    return GapCountResponse(
        recipe_id=recipe.id,
        label=recipe.label,
        count=count,
        source_table=recipe.source_table,
        target_table=recipe.target_table
    )


@router.get("/gaps/recipes/{recipe_id}/sample", response_model=GapSampleResponse, tags=["gaps"])
async def get_gap_recipe_sample(
    recipe_id: str = Path(..., description="The recipe ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of sample records to return"),
    country: Optional[str] = Query(None, description="Filter by country: 'United States', 'not United States', or omit for all")
):
    """Get sample records matching a gap recipe, optionally filtered by country."""
    if recipe_id not in RECIPES_BY_ID:
        raise HTTPException(status_code=404, detail=f"Recipe '{recipe_id}' not found")

    recipe = RECIPES_BY_ID[recipe_id]
    pool = get_pool()

    # Parse join columns (handles both 'col' and 'source_col:target_col' formats)
    source_col, target_col = parse_join_columns(recipe.join_column)

    # Build country filter if applicable
    country_join_clause, country_where_clause = build_country_filter(
        recipe.country_join, country, source_col
    )

    # Build the query based on comparison type
    if recipe.comparison == "not_in_target":
        query = f"""
            SELECT s.* FROM {recipe.source_table} s
            {country_join_clause}
            WHERE s.{source_col} IS NOT NULL
            AND s.{source_col} != ''
            {country_where_clause}
            AND NOT EXISTS (
                SELECT 1 FROM {recipe.target_table} t
                WHERE t.{target_col} = s.{source_col}
            )
            LIMIT $1
        """
    else:  # in_target
        query = f"""
            SELECT s.* FROM {recipe.source_table} s
            {country_join_clause}
            WHERE s.{source_col} IS NOT NULL
            AND s.{source_col} != ''
            {country_where_clause}
            AND EXISTS (
                SELECT 1 FROM {recipe.target_table} t
                WHERE t.{target_col} = s.{source_col}
            )
            LIMIT $1
        """

    rows = await pool.fetch(query, limit)

    # Get count too (remove LIMIT for count)
    count_query = query.replace("SELECT s.*", "SELECT COUNT(*)").replace("LIMIT $1", "")
    count = await pool.fetchval(count_query)

    return GapSampleResponse(
        recipe_id=recipe.id,
        label=recipe.label,
        count=count,
        sample=[row_to_dict(row) for row in rows],
        limit=limit
    )


def row_to_dict(row):
    """Convert asyncpg Record to dict, handling special types."""
    d = dict(row)
    for k, v in d.items():
        if hasattr(v, 'hex'):  # UUID
            d[k] = str(v)
        elif hasattr(v, 'isoformat'):  # datetime/date
            d[k] = v.isoformat()
    return d


# ============================================================
# ARCHIVED: Backfill Candidates - gaps we can fix from existing data
# Status: Timing out through asyncpg (works in psql). Archived 2026-01-31.
# ============================================================
#
# class BackfillCountResponse(BaseModel):
#     backfill_type: str
#     label: str
#     description: str
#     count: int
#     gap_table: str
#     source_table: str
#
#
# class BackfillSampleResponse(BaseModel):
#     backfill_type: str
#     label: str
#     count: int
#     sample: List[dict]
#     limit: int
#
#
# @router.get("/backfill/location/count", response_model=BackfillCountResponse, tags=["backfill"])
# async def get_backfill_location_count():
#     """
#     Get count of companies missing location in core.company_locations
#     that have location data available in extracted.company_discovery.
#     """
#     pool = get_pool()
#
#     query = """
#         SELECT COUNT(DISTINCT c.domain)
#         FROM core.companies c
#         WHERE NOT EXISTS (
#             SELECT 1 FROM core.company_locations cl WHERE cl.domain = c.domain
#         )
#         AND EXISTS (
#             SELECT 1 FROM extracted.company_discovery d
#             WHERE d.domain = c.domain
#             AND (d.matched_country IS NOT NULL OR d.country IS NOT NULL)
#         )
#     """
#
#     count = await pool.fetchval(query)
#
#     return BackfillCountResponse(
#         backfill_type="location",
#         label="Companies missing location (backfill available)",
#         description="Companies missing location in core.company_locations that have location data in extracted.company_discovery",
#         count=count,
#         gap_table="core.company_locations",
#         source_table="extracted.company_discovery"
#     )
#
#
# @router.get("/backfill/location/sample", response_model=BackfillSampleResponse, tags=["backfill"])
# async def get_backfill_location_sample(
#     limit: int = Query(10, ge=1, le=100, description="Number of sample records to return")
# ):
#     """
#     Get sample companies missing location with their available discovery data.
#     Returns the company domain along with the location data from extracted.company_discovery.
#     """
#     pool = get_pool()
#
#     query = """
#         SELECT
#             c.domain,
#             c.name as company_name,
#             d.country as discovery_country,
#             d.matched_country,
#             d.city as discovery_city,
#             d.matched_city,
#             d.state as discovery_state,
#             d.matched_state,
#             d.location as discovery_location_raw
#         FROM core.companies c
#         INNER JOIN extracted.company_discovery d ON d.domain = c.domain
#         WHERE NOT EXISTS (
#             SELECT 1 FROM core.company_locations cl WHERE cl.domain = c.domain
#         )
#         AND (d.matched_country IS NOT NULL OR d.country IS NOT NULL)
#         LIMIT $1
#     """
#
#     rows = await pool.fetch(query, limit)
#
#     # Get total count
#     count_query = """
#         SELECT COUNT(DISTINCT c.domain)
#         FROM core.companies c
#         WHERE NOT EXISTS (
#             SELECT 1 FROM core.company_locations cl WHERE cl.domain = c.domain
#         )
#         AND EXISTS (
#             SELECT 1 FROM extracted.company_discovery d
#             WHERE d.domain = c.domain
#             AND (d.matched_country IS NOT NULL OR d.country IS NOT NULL)
#         )
#     """
#     count = await pool.fetchval(count_query)
#
#     return BackfillSampleResponse(
#         backfill_type="location",
#         label="Companies missing location (backfill available)",
#         count=count,
#         sample=[row_to_dict(row) for row in rows],
#         limit=limit
#     )


# ============================================================
# extracted.company_discovery
# ============================================================

@router.get("/extracted/company_discovery/count", response_model=TableCountResponse)
async def get_extracted_company_discovery_count():
    """Get count of records in extracted.company_discovery."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM extracted.company_discovery")
    return TableCountResponse(
        schema_name="extracted",
        table_name="company_discovery",
        count=count
    )


@router.get("/extracted/company_discovery", response_model=TableDataResponse)
async def get_extracted_company_discovery(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    matched_industry: Optional[str] = Query(None, description="Filter by matched industry"),
    matched_country: Optional[str] = Query(None, description="Filter by matched country"),
    has_city: Optional[bool] = Query(None, description="Filter by has_city flag"),
    has_state: Optional[bool] = Query(None, description="Filter by has_state flag"),
    has_country: Optional[bool] = Query(None, description="Filter by has_country flag"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from extracted.company_discovery with optional filters."""
    pool = get_pool()

    # Build WHERE clause
    conditions = []
    params = []
    param_idx = 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if name:
        conditions.append(f"name ILIKE ${param_idx}")
        params.append(f"%{name}%")
        param_idx += 1
    if matched_industry:
        conditions.append(f"matched_industry = ${param_idx}")
        params.append(matched_industry)
        param_idx += 1
    if matched_country:
        conditions.append(f"matched_country = ${param_idx}")
        params.append(matched_country)
        param_idx += 1
    if has_city is not None:
        conditions.append(f"has_city = ${param_idx}")
        params.append(has_city)
        param_idx += 1
    if has_state is not None:
        conditions.append(f"has_state = ${param_idx}")
        params.append(has_state)
        param_idx += 1
    if has_country is not None:
        conditions.append(f"has_country = ${param_idx}")
        params.append(has_country)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get count
    count_query = f"SELECT COUNT(*) FROM extracted.company_discovery WHERE {where_clause}"
    total = await pool.fetchval(count_query, *params)

    # Get data
    data_query = f"""
        SELECT id, domain, name, linkedin_url, size, type, country, location,
               industry, matched_industry, city, state, matched_city, matched_state, matched_country,
               has_city, has_state, has_country, created_at, updated_at
        FROM extracted.company_discovery
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    rows = await pool.fetch(data_query, *params, limit, offset)

    return TableDataResponse(
        schema_name="extracted",
        table_name="company_discovery",
        data=[row_to_dict(row) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


# ============================================================
# core.companies (already has /api/companies, but adding count here for admin)
# ============================================================

@router.get("/core/companies/count", response_model=TableCountResponse)
async def get_core_companies_count():
    """Get count of records in core.companies."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.companies")
    return TableCountResponse(
        schema_name="core",
        table_name="companies",
        count=count
    )


# ============================================================
# Generic table count endpoint
# ============================================================

ALLOWED_TABLES = {
    # Core - Primary
    "core.companies",
    "core.people",
    "core.people_full",
    "core.leads",
    "core.company_customers",
    "core.person_past_employer",
    "core.person_work_history",
    # Core - Company Enrichment
    "core.company_descriptions",
    "core.company_industries",
    "core.company_locations",
    "core.company_employee_range",
    "core.company_funding",
    "core.company_revenue",
    "core.company_linkedin_urls",
    # Core - Person Enrichment
    "core.person_locations",
    "core.person_job_titles",
    "core.person_tenure",
    "core.person_promotions",
    "core.person_job_start_dates",
    # Core - VC & Investments
    "core.company_vc_backed",
    "core.company_vc_investments",
    "core.company_vc_investors",
    # Core - Case Studies & ICP
    "core.case_study_champions",
    "core.icp_criteria",
    # Core - Data Quality
    "core.companies_missing_cleaned_name",
    "core.companies_missing_location",
    "core.people_missing_country",
    "core.persons_missing_cleaned_title",
    "core.company_people_snapshot_history",
    # Core - Auxiliary
    "core.company_public",
    "core.company_employee_ranges",
    "core.target_client_views",
    # Extracted - All 50 tables
    "extracted.apollo_companies_cleaned",
    "extracted.apollo_instantdata_companies",
    "extracted.apollo_instantdata_people",
    "extracted.apollo_people_cleaned",
    "extracted.apollo_scrape",
    "extracted.case_study_buyers",
    "extracted.case_study_champions",
    "extracted.case_study_details",
    "extracted.cb_vc_portfolio",
    "extracted.clay_job_change",
    "extracted.clay_job_function_mapping",
    "extracted.clay_job_posting",
    "extracted.clay_new_hire",
    "extracted.clay_news_fundraising",
    "extracted.clay_promotion",
    "extracted.clay_seniority_mapping",
    "extracted.claygent_customers",
    "extracted.claygent_customers_structured",
    "extracted.claygent_customers_v2",
    "extracted.cleaned_company_names",
    "extracted.company_customer_claygent",
    "extracted.company_discovery",
    "extracted.company_discovery_location_parsed",
    "extracted.company_enrich_similar",
    "extracted.company_firmographics",
    "extracted.company_vc_investors",
    "extracted.crunchbase_domain_inference",
    "extracted.email_anymailfinder",
    "extracted.email_leadmagic",
    "extracted.icp_fit_criterion",
    "extracted.icp_industries",
    "extracted.icp_job_titles",
    "extracted.icp_value_proposition",
    "extracted.icp_verdict",
    "extracted.instant_data_scraper",
    "extracted.leadmagic_company_enrichment",
    "extracted.nostra_ecom_companies",
    "extracted.nostra_ecom_people",
    "extracted.person_discovery",
    "extracted.person_discovery_location_parsed",
    "extracted.person_education",
    "extracted.person_experience",
    "extracted.person_profile",
    "extracted.person_title_enrichment",
    "extracted.salesnav_scrapes_companies",
    "extracted.salesnav_scrapes_person",
    "extracted.signal_job_change",
    "extracted.signal_job_posting",
    "extracted.signal_promotion",
    "extracted.vc_portfolio",
    # Reference - All 39 tables
    "reference.apollo_companies_unmatched",
    "reference.apollo_people_unmatched_companies",
    "reference.apollo_people_unmatched_companies_deduped",
    "reference.business_models",
    "reference.clay_enriched_company_location_lookup",
    "reference.clay_find_companies_location_lookup",
    "reference.clay_find_people_location_lookup",
    "reference.companies_missing_cleaned_name",
    "reference.company_customers",
    "reference.company_icp",
    "reference.company_industries",
    "reference.company_location_lookup",
    "reference.company_types",
    "reference.countries",
    "reference.email_to_person",
    "reference.employee_range_lookup",
    "reference.employee_ranges",
    "reference.enrichment_workflow_registry",
    "reference.funding_range_lookup",
    "reference.funding_ranges",
    "reference.industry_lookup",
    "reference.job_functions",
    "reference.job_title_lookup",
    "reference.job_title_parsed",
    "reference.location_lookup",
    "reference.location_parsed",
    "reference.people_job_functions",
    "reference.people_seniority",
    "reference.person_discovery_missing_company",
    "reference.revenue_range_lookup",
    "reference.revenue_ranges",
    "reference.salesnav_company_location_lookup",
    "reference.salesnav_location_lookup",
    "reference.salesnav_people_job_title_lookup",
    "reference.seniorities",
    "reference.signal_registry",
    "reference.signals",
    "reference.us_cities",
    "reference.us_states",
    # Derived - 2 tables
    "derived.company_icp_industries_from_customers",
    "derived.icp_job_titles_from_champions",
    # Mapped - 3 tables
    "mapped.case_study_champions",
    "mapped.company_discovery",
    "mapped.person_discovery",
    # Staging - 6 tables
    "staging.case_study_urls_to_process",
    "staging.companies_to_enrich",
    "staging.forethought_icp_companies",
    "staging.forethought_icp_leads",
    "staging.forethought_icp_people",
    "staging.withcoverage_champions",
    # Raw - Phase 1: Core Discovery & Scrapes (13 tables)
    "raw.apollo_instantdata_scrapes",
    "raw.apollo_scrape",
    "raw.company_discovery",
    "raw.company_discovery_location_parsed",
    "raw.company_payloads",
    "raw.instant_data_scraper",
    "raw.person_discovery",
    "raw.person_discovery_location_parsed",
    "raw.person_payloads",
    "raw.person_title_enrichment",
    "raw.salesnav_scrapes",
    "raw.salesnav_scrapes_company_address_payloads",
    "raw.salesnav_scrapes_person_payloads",
    # Raw - Phase 2: Clay Webhooks (11 tables)
    "raw.clay_cleaned_company_names",
    "raw.clay_job_change_payloads",
    "raw.clay_job_function_mapping",
    "raw.clay_job_posting_payloads",
    "raw.clay_new_hire_payloads",
    "raw.clay_news_fundraising_payloads",
    "raw.clay_promotion_payloads",
    "raw.clay_seniority_mapping",
    "raw.claygent_customers_raw",
    "raw.claygent_customers_structured_raw",
    "raw.claygent_customers_v2_raw",
    # Raw - Phase 3: Signals (3 tables)
    "raw.signal_job_change_payloads",
    "raw.signal_job_posting_payloads",
    "raw.signal_promotion_payloads",
    # Raw - Phase 4: Company Enrichment (8 tables)
    "raw.company_customer_claygent_payloads",
    "raw.company_enrich_similar_batches",
    "raw.company_enrich_similar_queue",
    "raw.company_enrich_similar_raw",
    "raw.company_vc_investors",
    "raw.crunchbase_domain_inference_payloads",
    "raw.leadmagic_company_enrichment",
    "raw.manual_company_customers",
    # Raw - Phase 5: ICP, Case Studies, Email, VC, Misc (18 tables)
    "raw.case_study_buyers_payloads",
    "raw.case_study_extraction_payloads",
    "raw.cb_vc_portfolio_payloads",
    "raw.email_anymailfinder",
    "raw.email_leadmagic",
    "raw.email_waterfall_jobs",
    "raw.icp_fit_criterion",
    "raw.icp_industries",
    "raw.icp_job_titles",
    "raw.icp_payloads",
    "raw.icp_value_proposition",
    "raw.icp_verdict_payloads",
    "raw.nostra_ecom_companies",
    "raw.nostra_ecom_people",
    "raw.vc_crunchbase_portfolios",
    "raw.vc_firms",
    "raw.vc_portfolio_companies",
    "raw.vc_portfolio_payloads",
}


@router.get("/tables/{schema_name}/{table_name}/count", response_model=TableCountResponse)
async def get_table_count(schema_name: str, table_name: str):
    """Get count of records in a table. Limited to allowed tables for security."""
    full_name = f"{schema_name}.{table_name}"

    if full_name not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=403,
            detail=f"Table {full_name} not in allowed list. Allowed: {sorted(ALLOWED_TABLES)}"
        )

    pool = get_pool()
    count = await pool.fetchval(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")

    return TableCountResponse(
        schema_name=schema_name,
        table_name=table_name,
        count=count
    )


# ============================================================
# PHASE 1: Primary Entity Tables
# ============================================================

# ------------------------------------------------------------
# core.people (count only - data served via /api/people)
# ------------------------------------------------------------

@router.get("/core/people/count", response_model=TableCountResponse)
async def get_core_people_count():
    """Get count of records in core.people."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.people")
    return TableCountResponse(
        schema_name="core",
        table_name="people",
        count=count
    )


# ------------------------------------------------------------
# core.company_customers
# ------------------------------------------------------------

@router.get("/core/company_customers/count", response_model=TableCountResponse)
async def get_core_company_customers_count():
    """Get count of records in core.company_customers."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_customers")
    return TableCountResponse(
        schema_name="core",
        table_name="company_customers",
        count=count
    )


@router.get("/core/company_customers", response_model=TableDataResponse)
async def get_core_company_customers(
    origin_company_domain: Optional[str] = Query(None, description="Filter by origin company domain"),
    customer_domain: Optional[str] = Query(None, description="Filter by customer domain"),
    customer_name: Optional[str] = Query(None, description="Filter by customer name (partial match)"),
    has_case_study: Optional[bool] = Query(None, description="Filter by has_case_study flag"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_customers with optional filters."""
    pool = get_pool()

    conditions = []
    params = []
    param_idx = 1

    if origin_company_domain:
        conditions.append(f"origin_company_domain = ${param_idx}")
        params.append(origin_company_domain)
        param_idx += 1
    if customer_domain:
        conditions.append(f"customer_domain = ${param_idx}")
        params.append(customer_domain)
        param_idx += 1
    if customer_name:
        conditions.append(f"customer_name ILIKE ${param_idx}")
        params.append(f"%{customer_name}%")
        param_idx += 1
    if has_case_study is not None:
        conditions.append(f"has_case_study = ${param_idx}")
        params.append(has_case_study)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    count_query = f"SELECT COUNT(*) FROM core.company_customers WHERE {where_clause}"
    total = await pool.fetchval(count_query, *params)

    data_query = f"""
        SELECT id, origin_company_domain, origin_company_name, customer_name, customer_domain,
               case_study_url, has_case_study, source, created_at, updated_at
        FROM core.company_customers
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    rows = await pool.fetch(data_query, *params, limit, offset)

    return TableDataResponse(
        schema_name="core",
        table_name="company_customers",
        data=[row_to_dict(row) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


# ------------------------------------------------------------
# core.person_work_history
# ------------------------------------------------------------

@router.get("/core/person_work_history/count", response_model=TableCountResponse)
async def get_core_person_work_history_count():
    """Get count of records in core.person_work_history."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_work_history")
    return TableCountResponse(
        schema_name="core",
        table_name="person_work_history",
        count=count
    )


@router.get("/core/person_work_history", response_model=TableDataResponse)
async def get_core_person_work_history(
    linkedin_url: Optional[str] = Query(None, description="Filter by person LinkedIn URL"),
    company_domain: Optional[str] = Query(None, description="Filter by company domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    matched_job_function: Optional[str] = Query(None, description="Filter by job function"),
    matched_seniority: Optional[str] = Query(None, description="Filter by seniority"),
    is_current: Optional[bool] = Query(None, description="Filter by is_current flag"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_work_history with optional filters."""
    pool = get_pool()

    conditions = []
    params = []
    param_idx = 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if company_domain:
        conditions.append(f"company_domain = ${param_idx}")
        params.append(company_domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1
    if matched_job_function:
        conditions.append(f"matched_job_function = ${param_idx}")
        params.append(matched_job_function)
        param_idx += 1
    if matched_seniority:
        conditions.append(f"matched_seniority = ${param_idx}")
        params.append(matched_seniority)
        param_idx += 1
    if is_current is not None:
        conditions.append(f"is_current = ${param_idx}")
        params.append(is_current)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    count_query = f"SELECT COUNT(*) FROM core.person_work_history WHERE {where_clause}"
    total = await pool.fetchval(count_query, *params)

    data_query = f"""
        SELECT id, linkedin_url, company_domain, company_name, company_linkedin_url,
               title, matched_job_function, matched_seniority,
               start_date, end_date, is_current, experience_order, created_at
        FROM core.person_work_history
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    rows = await pool.fetch(data_query, *params, limit, offset)

    return TableDataResponse(
        schema_name="core",
        table_name="person_work_history",
        data=[row_to_dict(row) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


# ------------------------------------------------------------
# core.person_past_employer
# ------------------------------------------------------------

@router.get("/core/person_past_employer/count", response_model=TableCountResponse)
async def get_core_person_past_employer_count():
    """Get count of records in core.person_past_employer."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_past_employer")
    return TableCountResponse(
        schema_name="core",
        table_name="person_past_employer",
        count=count
    )


@router.get("/core/person_past_employer", response_model=TableDataResponse)
async def get_core_person_past_employer(
    linkedin_url: Optional[str] = Query(None, description="Filter by person LinkedIn URL"),
    past_company_domain: Optional[str] = Query(None, description="Filter by past company domain"),
    past_company_name: Optional[str] = Query(None, description="Filter by past company name (partial match)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_past_employer with optional filters."""
    pool = get_pool()

    conditions = []
    params = []
    param_idx = 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if past_company_domain:
        conditions.append(f"past_company_domain = ${param_idx}")
        params.append(past_company_domain)
        param_idx += 1
    if past_company_name:
        conditions.append(f"past_company_name ILIKE ${param_idx}")
        params.append(f"%{past_company_name}%")
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    count_query = f"SELECT COUNT(*) FROM core.person_past_employer WHERE {where_clause}"
    total = await pool.fetchval(count_query, *params)

    data_query = f"""
        SELECT id, linkedin_url, past_company_name, past_company_domain, source, created_at
        FROM core.person_past_employer
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    rows = await pool.fetch(data_query, *params, limit, offset)

    return TableDataResponse(
        schema_name="core",
        table_name="person_past_employer",
        data=[row_to_dict(row) for row in rows],
        meta=PaginationMeta(total=total, limit=limit, offset=offset)
    )


# ============================================================
# PHASE 2: Company Enrichment Tables
# ============================================================

# ------------------------------------------------------------
# core.company_descriptions
# ------------------------------------------------------------

@router.get("/core/company_descriptions/count", response_model=TableCountResponse)
async def get_core_company_descriptions_count():
    """Get count of records in core.company_descriptions."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_descriptions")
    return TableCountResponse(schema_name="core", table_name="company_descriptions", count=count)


@router.get("/core/company_descriptions", response_model=TableDataResponse)
async def get_core_company_descriptions(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    source: Optional[str] = Query(None, description="Filter by source"),
    has_description: Optional[bool] = Query(None, description="Filter by whether description exists"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_descriptions with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1
    if has_description is not None:
        if has_description:
            conditions.append("description IS NOT NULL AND description != ''")
        else:
            conditions.append("(description IS NULL OR description = '')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_descriptions WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, description, tagline, source, created_at, updated_at
        FROM core.company_descriptions WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_descriptions",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_industries
# ------------------------------------------------------------

@router.get("/core/company_industries/count", response_model=TableCountResponse)
async def get_core_company_industries_count():
    """Get count of records in core.company_industries."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_industries")
    return TableCountResponse(schema_name="core", table_name="company_industries", count=count)


@router.get("/core/company_industries", response_model=TableDataResponse)
async def get_core_company_industries(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    matched_industry: Optional[str] = Query(None, description="Filter by matched industry"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_industries with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if matched_industry:
        conditions.append(f"matched_industry = ${param_idx}")
        params.append(matched_industry)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_industries WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, matched_industry, source, created_at, updated_at
        FROM core.company_industries WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_industries",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_locations
# ------------------------------------------------------------

@router.get("/core/company_locations/count", response_model=TableCountResponse)
async def get_core_company_locations_count():
    """Get count of records in core.company_locations."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_locations")
    return TableCountResponse(schema_name="core", table_name="company_locations", count=count)


@router.get("/core/company_locations", response_model=TableDataResponse)
async def get_core_company_locations(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    state: Optional[str] = Query(None, description="Filter by state (partial match)"),
    country: Optional[str] = Query(None, description="Filter by country (partial match)"),
    has_city: Optional[bool] = Query(None, description="Filter by has_city flag"),
    has_state: Optional[bool] = Query(None, description="Filter by has_state flag"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_locations with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if city:
        conditions.append(f"city ILIKE ${param_idx}")
        params.append(f"%{city}%")
        param_idx += 1
    if state:
        conditions.append(f"state ILIKE ${param_idx}")
        params.append(f"%{state}%")
        param_idx += 1
    if country:
        conditions.append(f"country ILIKE ${param_idx}")
        params.append(f"%{country}%")
        param_idx += 1
    if has_city is not None:
        conditions.append(f"has_city = ${param_idx}")
        params.append(has_city)
        param_idx += 1
    if has_state is not None:
        conditions.append(f"has_state = ${param_idx}")
        params.append(has_state)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_locations WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, city, state, country, raw_location, raw_country, has_city, has_state, source, created_at, updated_at
        FROM core.company_locations WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_locations",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_employee_range
# ------------------------------------------------------------

@router.get("/core/company_employee_range/count", response_model=TableCountResponse)
async def get_core_company_employee_range_count():
    """Get count of records in core.company_employee_range."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_employee_range")
    return TableCountResponse(schema_name="core", table_name="company_employee_range", count=count)


@router.get("/core/company_employee_range", response_model=TableDataResponse)
async def get_core_company_employee_range(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    employee_range: Optional[str] = Query(None, description="Filter by employee range"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_employee_range with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if employee_range:
        conditions.append(f"employee_range = ${param_idx}")
        params.append(employee_range)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_employee_range WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, employee_range, source, created_at, updated_at
        FROM core.company_employee_range WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_employee_range",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_funding
# ------------------------------------------------------------

@router.get("/core/company_funding/count", response_model=TableCountResponse)
async def get_core_company_funding_count():
    """Get count of records in core.company_funding."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_funding")
    return TableCountResponse(schema_name="core", table_name="company_funding", count=count)


@router.get("/core/company_funding", response_model=TableDataResponse)
async def get_core_company_funding(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    matched_funding_range: Optional[str] = Query(None, description="Filter by matched funding range"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_funding with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if matched_funding_range:
        conditions.append(f"matched_funding_range = ${param_idx}")
        params.append(matched_funding_range)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_funding WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, source, raw_funding_range, raw_funding_amount, matched_funding_range, created_at, updated_at
        FROM core.company_funding WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_funding",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_revenue
# ------------------------------------------------------------

@router.get("/core/company_revenue/count", response_model=TableCountResponse)
async def get_core_company_revenue_count():
    """Get count of records in core.company_revenue."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_revenue")
    return TableCountResponse(schema_name="core", table_name="company_revenue", count=count)


@router.get("/core/company_revenue", response_model=TableDataResponse)
async def get_core_company_revenue(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    matched_revenue_range: Optional[str] = Query(None, description="Filter by matched revenue range"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_revenue with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if matched_revenue_range:
        conditions.append(f"matched_revenue_range = ${param_idx}")
        params.append(matched_revenue_range)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_revenue WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, source, raw_revenue_range, raw_revenue_amount, matched_revenue_range, created_at, updated_at
        FROM core.company_revenue WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_revenue",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_linkedin_urls
# ------------------------------------------------------------

@router.get("/core/company_linkedin_urls/count", response_model=TableCountResponse)
async def get_core_company_linkedin_urls_count():
    """Get count of records in core.company_linkedin_urls."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_linkedin_urls")
    return TableCountResponse(schema_name="core", table_name="company_linkedin_urls", count=count)


@router.get("/core/company_linkedin_urls", response_model=TableDataResponse)
async def get_core_company_linkedin_urls(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL (partial match)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_linkedin_urls with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if linkedin_url:
        conditions.append(f"linkedin_url ILIKE ${param_idx}")
        params.append(f"%{linkedin_url}%")
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_linkedin_urls WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, linkedin_url, source, created_at, updated_at
        FROM core.company_linkedin_urls WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_linkedin_urls",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ============================================================
# PHASE 3: Person Enrichment Tables
# ============================================================

# ------------------------------------------------------------
# core.person_locations
# ------------------------------------------------------------

@router.get("/core/person_locations/count", response_model=TableCountResponse)
async def get_core_person_locations_count():
    """Get count of records in core.person_locations."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_locations")
    return TableCountResponse(schema_name="core", table_name="person_locations", count=count)


@router.get("/core/person_locations", response_model=TableDataResponse)
async def get_core_person_locations(
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    city: Optional[str] = Query(None, description="Filter by city (partial match)"),
    state: Optional[str] = Query(None, description="Filter by state (partial match)"),
    country: Optional[str] = Query(None, description="Filter by country (partial match)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_locations with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if city:
        conditions.append(f"city ILIKE ${param_idx}")
        params.append(f"%{city}%")
        param_idx += 1
    if state:
        conditions.append(f"state ILIKE ${param_idx}")
        params.append(f"%{state}%")
        param_idx += 1
    if country:
        conditions.append(f"country ILIKE ${param_idx}")
        params.append(f"%{country}%")
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.person_locations WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, linkedin_url, city, state, country, source, created_at, updated_at
        FROM core.person_locations WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="person_locations",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.person_job_titles
# ------------------------------------------------------------

@router.get("/core/person_job_titles/count", response_model=TableCountResponse)
async def get_core_person_job_titles_count():
    """Get count of records in core.person_job_titles."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_job_titles")
    return TableCountResponse(schema_name="core", table_name="person_job_titles", count=count)


@router.get("/core/person_job_titles", response_model=TableDataResponse)
async def get_core_person_job_titles(
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    matched_cleaned_job_title: Optional[str] = Query(None, description="Filter by job title (partial match)"),
    matched_job_function: Optional[str] = Query(None, description="Filter by job function"),
    matched_seniority: Optional[str] = Query(None, description="Filter by seniority"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_job_titles with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if matched_cleaned_job_title:
        conditions.append(f"matched_cleaned_job_title ILIKE ${param_idx}")
        params.append(f"%{matched_cleaned_job_title}%")
        param_idx += 1
    if matched_job_function:
        conditions.append(f"matched_job_function = ${param_idx}")
        params.append(matched_job_function)
        param_idx += 1
    if matched_seniority:
        conditions.append(f"matched_seniority = ${param_idx}")
        params.append(matched_seniority)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.person_job_titles WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, linkedin_url, matched_cleaned_job_title, matched_job_function, matched_seniority, source, created_at, updated_at
        FROM core.person_job_titles WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="person_job_titles",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.person_tenure
# ------------------------------------------------------------

@router.get("/core/person_tenure/count", response_model=TableCountResponse)
async def get_core_person_tenure_count():
    """Get count of records in core.person_tenure."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_tenure")
    return TableCountResponse(schema_name="core", table_name="person_tenure", count=count)


@router.get("/core/person_tenure", response_model=TableDataResponse)
async def get_core_person_tenure(
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    job_start_date_gte: Optional[str] = Query(None, description="Filter by job start date >= (YYYY-MM-DD)"),
    job_start_date_lte: Optional[str] = Query(None, description="Filter by job start date <= (YYYY-MM-DD)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_tenure with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if job_start_date_gte:
        conditions.append(f"job_start_date >= ${param_idx}")
        params.append(job_start_date_gte)
        param_idx += 1
    if job_start_date_lte:
        conditions.append(f"job_start_date <= ${param_idx}")
        params.append(job_start_date_lte)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.person_tenure WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, linkedin_url, job_start_date, source, created_at, updated_at
        FROM core.person_tenure WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="person_tenure",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.person_promotions
# ------------------------------------------------------------

@router.get("/core/person_promotions/count", response_model=TableCountResponse)
async def get_core_person_promotions_count():
    """Get count of records in core.person_promotions."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_promotions")
    return TableCountResponse(schema_name="core", table_name="person_promotions", count=count)


@router.get("/core/person_promotions", response_model=TableDataResponse)
async def get_core_person_promotions(
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    company_domain: Optional[str] = Query(None, description="Filter by company domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    promotion_date_gte: Optional[str] = Query(None, description="Filter by promotion date >= (YYYY-MM-DD)"),
    promotion_date_lte: Optional[str] = Query(None, description="Filter by promotion date <= (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_promotions with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if company_domain:
        conditions.append(f"company_domain = ${param_idx}")
        params.append(company_domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1
    if promotion_date_gte:
        conditions.append(f"promotion_date >= ${param_idx}")
        params.append(promotion_date_gte)
        param_idx += 1
    if promotion_date_lte:
        conditions.append(f"promotion_date <= ${param_idx}")
        params.append(promotion_date_lte)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.person_promotions WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, linkedin_url, company_domain, company_name, previous_title, new_title, promotion_date, created_at
        FROM core.person_promotions WHERE {where_clause}
        ORDER BY promotion_date DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="person_promotions",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.person_job_start_dates
# ------------------------------------------------------------

@router.get("/core/person_job_start_dates/count", response_model=TableCountResponse)
async def get_core_person_job_start_dates_count():
    """Get count of records in core.person_job_start_dates."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.person_job_start_dates")
    return TableCountResponse(schema_name="core", table_name="person_job_start_dates", count=count)


@router.get("/core/person_job_start_dates", response_model=TableDataResponse)
async def get_core_person_job_start_dates(
    person_linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    job_start_date_gte: Optional[str] = Query(None, description="Filter by job start date >= (YYYY-MM-DD)"),
    job_start_date_lte: Optional[str] = Query(None, description="Filter by job start date <= (YYYY-MM-DD)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.person_job_start_dates with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if person_linkedin_url:
        conditions.append(f"person_linkedin_url = ${param_idx}")
        params.append(person_linkedin_url)
        param_idx += 1
    if job_start_date_gte:
        conditions.append(f"job_start_date >= ${param_idx}")
        params.append(job_start_date_gte)
        param_idx += 1
    if job_start_date_lte:
        conditions.append(f"job_start_date <= ${param_idx}")
        params.append(job_start_date_lte)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.person_job_start_dates WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, person_linkedin_url, job_start_date, source, created_at
        FROM core.person_job_start_dates WHERE {where_clause}
        ORDER BY job_start_date DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="person_job_start_dates",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ============================================================
# PHASE 4: VC & Investment Tables
# ============================================================

# ------------------------------------------------------------
# core.company_vc_backed
# ------------------------------------------------------------

@router.get("/core/company_vc_backed/count", response_model=TableCountResponse)
async def get_core_company_vc_backed_count():
    """Get count of records in core.company_vc_backed."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_vc_backed")
    return TableCountResponse(schema_name="core", table_name="company_vc_backed", count=count)


@router.get("/core/company_vc_backed", response_model=TableDataResponse)
async def get_core_company_vc_backed(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    vc_count_gte: Optional[int] = Query(None, description="Filter by VC count >="),
    vc_count_lte: Optional[int] = Query(None, description="Filter by VC count <="),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_vc_backed with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if vc_count_gte is not None:
        conditions.append(f"vc_count >= ${param_idx}")
        params.append(vc_count_gte)
        param_idx += 1
    if vc_count_lte is not None:
        conditions.append(f"vc_count <= ${param_idx}")
        params.append(vc_count_lte)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_vc_backed WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT domain, vc_count, created_at
        FROM core.company_vc_backed WHERE {where_clause}
        ORDER BY vc_count DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_vc_backed",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_vc_investments
# ------------------------------------------------------------

@router.get("/core/company_vc_investments/count", response_model=TableCountResponse)
async def get_core_company_vc_investments_count():
    """Get count of records in core.company_vc_investments."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_vc_investments")
    return TableCountResponse(schema_name="core", table_name="company_vc_investments", count=count)


@router.get("/core/company_vc_investments", response_model=TableDataResponse)
async def get_core_company_vc_investments(
    company_domain: Optional[str] = Query(None, description="Filter by company domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    vc_name: Optional[str] = Query(None, description="Filter by VC name (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_vc_investments with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if company_domain:
        conditions.append(f"company_domain = ${param_idx}")
        params.append(company_domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1
    if vc_name:
        conditions.append(f"vc_name ILIKE ${param_idx}")
        params.append(f"%{vc_name}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_vc_investments WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, company_domain, company_name, vc_name, created_at
        FROM core.company_vc_investments WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_vc_investments",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_vc_investors
# ------------------------------------------------------------

@router.get("/core/company_vc_investors/count", response_model=TableCountResponse)
async def get_core_company_vc_investors_count():
    """Get count of records in core.company_vc_investors."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_vc_investors")
    return TableCountResponse(schema_name="core", table_name="company_vc_investors", count=count)


@router.get("/core/company_vc_investors", response_model=TableDataResponse)
async def get_core_company_vc_investors(
    company_domain: Optional[str] = Query(None, description="Filter by company domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    vc_name: Optional[str] = Query(None, description="Filter by VC name (partial match)"),
    vc_domain: Optional[str] = Query(None, description="Filter by VC domain"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_vc_investors with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if company_domain:
        conditions.append(f"company_domain = ${param_idx}")
        params.append(company_domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1
    if vc_name:
        conditions.append(f"vc_name ILIKE ${param_idx}")
        params.append(f"%{vc_name}%")
        param_idx += 1
    if vc_domain:
        conditions.append(f"vc_domain = ${param_idx}")
        params.append(vc_domain)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_vc_investors WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, company_domain, company_name, vc_name, vc_domain, source, created_at
        FROM core.company_vc_investors WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_vc_investors",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ============================================================
# PHASE 5: Case Studies & ICP
# ============================================================

# ------------------------------------------------------------
# core.case_study_champions
# ------------------------------------------------------------

@router.get("/core/case_study_champions/count", response_model=TableCountResponse)
async def get_core_case_study_champions_count():
    """Get count of records in core.case_study_champions."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.case_study_champions")
    return TableCountResponse(schema_name="core", table_name="case_study_champions", count=count)


@router.get("/core/case_study_champions", response_model=TableDataResponse)
async def get_core_case_study_champions(
    full_name: Optional[str] = Query(None, description="Filter by full name (partial match)"),
    job_title: Optional[str] = Query(None, description="Filter by job title (partial match)"),
    company_domain: Optional[str] = Query(None, description="Filter by company domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    origin_company_domain: Optional[str] = Query(None, description="Filter by origin company domain"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.case_study_champions with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if full_name:
        conditions.append(f"full_name ILIKE ${param_idx}")
        params.append(f"%{full_name}%")
        param_idx += 1
    if job_title:
        conditions.append(f"job_title ILIKE ${param_idx}")
        params.append(f"%{job_title}%")
        param_idx += 1
    if company_domain:
        conditions.append(f"company_domain = ${param_idx}")
        params.append(company_domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1
    if origin_company_domain:
        conditions.append(f"origin_company_domain = ${param_idx}")
        params.append(origin_company_domain)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.case_study_champions WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, full_name, job_title, company_name, company_domain, origin_company_domain,
               case_study_url, source, core_person_id, core_company_id, created_at, updated_at
        FROM core.case_study_champions WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="case_study_champions",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.icp_criteria
# ------------------------------------------------------------

@router.get("/core/icp_criteria/count", response_model=TableCountResponse)
async def get_core_icp_criteria_count():
    """Get count of records in core.icp_criteria."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.icp_criteria")
    return TableCountResponse(schema_name="core", table_name="icp_criteria", count=count)


@router.get("/core/icp_criteria", response_model=TableDataResponse)
async def get_core_icp_criteria(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.icp_criteria with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.icp_criteria WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, company_name, industries, countries, employee_ranges, funding_stages,
               job_titles, seniorities, job_functions, value_proposition, core_benefit,
               target_customer, key_differentiator, created_at, updated_at
        FROM core.icp_criteria WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="icp_criteria",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ============================================================
# PHASE 6: Data Quality / Gap Analysis Tables
# ============================================================

# ------------------------------------------------------------
# core.companies_missing_cleaned_name
# ------------------------------------------------------------

@router.get("/core/companies_missing_cleaned_name/count", response_model=TableCountResponse)
async def get_core_companies_missing_cleaned_name_count():
    """Get count of records in core.companies_missing_cleaned_name."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.companies_missing_cleaned_name")
    return TableCountResponse(schema_name="core", table_name="companies_missing_cleaned_name", count=count)


@router.get("/core/companies_missing_cleaned_name", response_model=TableDataResponse)
async def get_core_companies_missing_cleaned_name(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.companies_missing_cleaned_name with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if name:
        conditions.append(f"name ILIKE ${param_idx}")
        params.append(f"%{name}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.companies_missing_cleaned_name WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, name, domain, linkedin_url
        FROM core.companies_missing_cleaned_name WHERE {where_clause}
        ORDER BY domain LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="companies_missing_cleaned_name",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.companies_missing_location
# ------------------------------------------------------------

@router.get("/core/companies_missing_location/count", response_model=TableCountResponse)
async def get_core_companies_missing_location_count():
    """Get count of records in core.companies_missing_location."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.companies_missing_location")
    return TableCountResponse(schema_name="core", table_name="companies_missing_location", count=count)


@router.get("/core/companies_missing_location", response_model=TableDataResponse)
async def get_core_companies_missing_location(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.companies_missing_location with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if name:
        conditions.append(f"name ILIKE ${param_idx}")
        params.append(f"%{name}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.companies_missing_location WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, name, linkedin_url, discovery_location, salesnav_location
        FROM core.companies_missing_location WHERE {where_clause}
        ORDER BY domain LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="companies_missing_location",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.people_missing_country
# ------------------------------------------------------------

@router.get("/core/people_missing_country/count", response_model=TableCountResponse)
async def get_core_people_missing_country_count():
    """Get count of records in core.people_missing_country."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.people_missing_country")
    return TableCountResponse(schema_name="core", table_name="people_missing_country", count=count)


@router.get("/core/people_missing_country", response_model=TableDataResponse)
async def get_core_people_missing_country(
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    full_name: Optional[str] = Query(None, description="Filter by full name (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.people_missing_country with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if full_name:
        conditions.append(f"full_name ILIKE ${param_idx}")
        params.append(f"%{full_name}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.people_missing_country WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, linkedin_url, full_name, profile_location, discovery_location, salesnav_location
        FROM core.people_missing_country WHERE {where_clause}
        ORDER BY linkedin_url LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="people_missing_country",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.persons_missing_cleaned_title
# ------------------------------------------------------------

@router.get("/core/persons_missing_cleaned_title/count", response_model=TableCountResponse)
async def get_core_persons_missing_cleaned_title_count():
    """Get count of records in core.persons_missing_cleaned_title."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.persons_missing_cleaned_title")
    return TableCountResponse(schema_name="core", table_name="persons_missing_cleaned_title", count=count)


@router.get("/core/persons_missing_cleaned_title", response_model=TableDataResponse)
async def get_core_persons_missing_cleaned_title(
    linkedin_url: Optional[str] = Query(None, description="Filter by LinkedIn URL"),
    raw_job_title: Optional[str] = Query(None, description="Filter by raw job title (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.persons_missing_cleaned_title with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if linkedin_url:
        conditions.append(f"linkedin_url = ${param_idx}")
        params.append(linkedin_url)
        param_idx += 1
    if raw_job_title:
        conditions.append(f"raw_job_title ILIKE ${param_idx}")
        params.append(f"%{raw_job_title}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.persons_missing_cleaned_title WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT linkedin_url, raw_job_title, cleaned_job_title, matched_job_function, matched_seniority, created_at
        FROM core.persons_missing_cleaned_title WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="persons_missing_cleaned_title",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_people_snapshot_history
# ------------------------------------------------------------

@router.get("/core/company_people_snapshot_history/count", response_model=TableCountResponse)
async def get_core_company_people_snapshot_history_count():
    """Get count of records in core.company_people_snapshot_history."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_people_snapshot_history")
    return TableCountResponse(schema_name="core", table_name="company_people_snapshot_history", count=count)


@router.get("/core/company_people_snapshot_history", response_model=TableDataResponse)
async def get_core_company_people_snapshot_history(
    company_domain: Optional[str] = Query(None, description="Filter by company domain"),
    snapshot_date_gte: Optional[str] = Query(None, description="Filter by snapshot date >= (YYYY-MM-DD)"),
    snapshot_date_lte: Optional[str] = Query(None, description="Filter by snapshot date <= (YYYY-MM-DD)"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_people_snapshot_history with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if company_domain:
        conditions.append(f"company_domain = ${param_idx}")
        params.append(company_domain)
        param_idx += 1
    if snapshot_date_gte:
        conditions.append(f"snapshot_date >= ${param_idx}")
        params.append(snapshot_date_gte)
        param_idx += 1
    if snapshot_date_lte:
        conditions.append(f"snapshot_date <= ${param_idx}")
        params.append(snapshot_date_lte)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_people_snapshot_history WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, company_domain, snapshot_date, total_people_count, people_added_count, people_removed_count, source, created_at
        FROM core.company_people_snapshot_history WHERE {where_clause}
        ORDER BY snapshot_date DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_people_snapshot_history",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ============================================================
# PHASE 7: Auxiliary Tables
# ============================================================

# ------------------------------------------------------------
# core.company_public
# ------------------------------------------------------------

@router.get("/core/company_public/count", response_model=TableCountResponse)
async def get_core_company_public_count():
    """Get count of records in core.company_public."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_public")
    return TableCountResponse(schema_name="core", table_name="company_public", count=count)


@router.get("/core/company_public", response_model=TableDataResponse)
async def get_core_company_public(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    company_name: Optional[str] = Query(None, description="Filter by company name (partial match)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_public with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if company_name:
        conditions.append(f"company_name ILIKE ${param_idx}")
        params.append(f"%{company_name}%")
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_public WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT domain, company_name, linkedin_url, created_at
        FROM core.company_public WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_public",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.company_employee_ranges
# ------------------------------------------------------------

@router.get("/core/company_employee_ranges/count", response_model=TableCountResponse)
async def get_core_company_employee_ranges_count():
    """Get count of records in core.company_employee_ranges."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.company_employee_ranges")
    return TableCountResponse(schema_name="core", table_name="company_employee_ranges", count=count)


@router.get("/core/company_employee_ranges", response_model=TableDataResponse)
async def get_core_company_employee_ranges(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    matched_employee_range: Optional[str] = Query(None, description="Filter by matched employee range"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.company_employee_ranges with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if matched_employee_range:
        conditions.append(f"matched_employee_range = ${param_idx}")
        params.append(matched_employee_range)
        param_idx += 1
    if source:
        conditions.append(f"source = ${param_idx}")
        params.append(source)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.company_employee_ranges WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, source, raw_size, raw_employee_count, matched_employee_range, created_at, updated_at
        FROM core.company_employee_ranges WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="company_employee_ranges",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ------------------------------------------------------------
# core.target_client_views
# ------------------------------------------------------------

@router.get("/core/target_client_views/count", response_model=TableCountResponse)
async def get_core_target_client_views_count():
    """Get count of records in core.target_client_views."""
    pool = get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM core.target_client_views")
    return TableCountResponse(schema_name="core", table_name="target_client_views", count=count)


@router.get("/core/target_client_views", response_model=TableDataResponse)
async def get_core_target_client_views(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    slug: Optional[str] = Query(None, description="Filter by slug"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get records from core.target_client_views with optional filters."""
    pool = get_pool()
    conditions, params, param_idx = [], [], 1

    if domain:
        conditions.append(f"domain = ${param_idx}")
        params.append(domain)
        param_idx += 1
    if name:
        conditions.append(f"name ILIKE ${param_idx}")
        params.append(f"%{name}%")
        param_idx += 1
    if slug:
        conditions.append(f"slug = ${param_idx}")
        params.append(slug)
        param_idx += 1

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    total = await pool.fetchval(f"SELECT COUNT(*) FROM core.target_client_views WHERE {where_clause}", *params)

    rows = await pool.fetch(f"""
        SELECT id, domain, name, slug, filters, endpoint, created_at, updated_at
        FROM core.target_client_views WHERE {where_clause}
        ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """, *params, limit, offset)

    return TableDataResponse(schema_name="core", table_name="target_client_views",
        data=[row_to_dict(row) for row in rows], meta=PaginationMeta(total=total, limit=limit, offset=offset))


# ============================================================
# Generic endpoint for any schema/table (must be LAST to not override specific routes)
# ============================================================

@router.get("/{schema_name}/{table_name}/count", response_model=TableCountResponse)
async def get_generic_table_count(schema_name: str, table_name: str):
    """
    Generic count endpoint for any allowed table.
    This endpoint must be defined LAST so specific routes take precedence.
    """
    full_name = f"{schema_name}.{table_name}"

    if full_name not in ALLOWED_TABLES:
        raise HTTPException(
            status_code=403,
            detail=f"Table {full_name} not in allowed list"
        )

    pool = get_pool()
    count = await pool.fetchval(f"SELECT COUNT(*) FROM {schema_name}.{table_name}")

    return TableCountResponse(
        schema_name=schema_name,
        table_name=table_name,
        count=count
    )
