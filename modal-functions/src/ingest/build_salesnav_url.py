"""
SalesNav URL Constructor

Deterministic URL construction — NO LLM.
Takes structured inputs and outputs a fully encoded LinkedIn Sales Navigator
search URL ready to be sent to the RapidAPI scraper endpoint.

Double-encoding: spaces → %2520, colons → %253A, etc.
"""

import modal
from urllib.parse import quote
from pydantic import BaseModel, Field
from typing import List, Optional

from config import app, image


class BuildSalesNavURLRequest(BaseModel):
    orgId: str = Field(min_length=1, description="LinkedIn numeric org ID")
    companyName: str = Field(min_length=1, description="Company name as it appears on LinkedIn")
    titles: List[str] = Field(min_length=1, description="Job titles to target")
    excludedSeniority: Optional[List[str]] = Field(default=["Entry Level"], description="Seniority levels to exclude")
    regions: Optional[List[str]] = Field(default=["North America"], description="Person location filter")
    companyHQRegions: Optional[List[str]] = Field(default=["North America"], description="Company HQ location filter")
    companyHeadcount: Optional[List[str]] = Field(default=None, description="Company headcount ranges")
    function: Optional[List[str]] = Field(default=None, description="Job functions (e.g. 'Sales', 'Engineering')")


# Seniority level IDs
SENIORITY_IDS = {
    "Entry Level": "110",
    "Training": "1",
    "Unpaid": "2",
    "Senior": "3",
    "Manager": "4",
    "Director": "5",
    "VP": "6",
    "CXO": "7",
    "Partner": "8",
    "Owner": "9",
}

# Headcount range IDs
HEADCOUNT_IDS = {
    "Self-employed": "A",
    "1-10": "B",
    "11-50": "C",
    "51-200": "D",
    "201-500": "E",
    "501-1000": "F",
    "1001-5000": "G",
    "5001-10,000": "H",
    "10,000+": "I",
}

# Function IDs
FUNCTION_IDS = {
    "Accounting": "1",
    "Administrative": "2",
    "Arts and Design": "3",
    "Business Development": "4",
    "Community & Social Services": "5",
    "Consulting": "6",
    "Education": "7",
    "Engineering": "8",
    "Entrepreneurship": "9",
    "Finance": "10",
    "Healthcare Services": "11",
    "Human Resources": "12",
    "Information Technology": "13",
    "Legal": "14",
    "Marketing": "15",
    "Media & Communications": "16",
    "Military & Protective Services": "17",
    "Operations": "18",
    "Product Management": "19",
    "Program & Project Management": "20",
    "Purchasing": "21",
    "Quality Assurance": "22",
    "Real Estate": "23",
    "Research": "24",
    "Sales": "25",
    "Support": "26",
}

# Region IDs (common ones)
REGION_IDS = {
    "North America": "102221843",
    "United States": "103644278",
    "Canada": "101174742",
    "Europe": "100506914",
    "United Kingdom": "101165590",
    "Asia": "102393603",
    "Australia": "101452733",
    "EMEA": "91000000",  # LinkedIn's EMEA geo
    "APAC": "102393603",
    "Latin America": "104514572",
}


def double_encode(s: str) -> str:
    """Double URL encode: first encode, then encode the % signs."""
    # First pass: normal URL encoding
    once = quote(s, safe="")
    # Second pass: encode the % from first pass
    twice = once.replace("%", "%25")
    return twice


def build_filter_value(type_name: str, values: List[dict]) -> str:
    """Build a single filter entry."""
    values_str = ",".join(
        f"({','.join(f'{k}%3A{v}' for k, v in val.items())})"
        for val in values
    )
    return f"(type%3A{type_name}%2Cvalues%3AList({values_str}))"


@app.function(
    image=image,
    timeout=300,
)
@modal.fastapi_endpoint(method="POST")
def build_salesnav_url(request: BuildSalesNavURLRequest) -> dict:
    """
    Construct a LinkedIn Sales Navigator search URL.
    Pure programmatic construction — no LLM.
    """
    try:
        filters = []

        # PAST_COMPANY filter (INCLUDED)
        org_urn = double_encode(f"urn:li:organization:{request.orgId}")
        company_text = double_encode(request.companyName)
        filters.append(
            f"(type%3APAST_COMPANY%2Cvalues%3AList((id%3A{org_urn}%2Ctext%3A{company_text}%2CselectionType%3AINCLUDED%2Cparent%3A(id%3A0))))"
        )

        # CURRENT_COMPANY filter (EXCLUDED)
        filters.append(
            f"(type%3ACURRENT_COMPANY%2Cvalues%3AList((id%3A{org_urn}%2Ctext%3A{company_text}%2CselectionType%3AEXCLUDED%2Cparent%3A(id%3A0))))"
        )

        # CURRENT_TITLE filter
        title_values = []
        for title in request.titles:
            encoded_title = double_encode(title)
            title_values.append(f"(text%3A{encoded_title}%2CselectionType%3AINCLUDED)")
        filters.append(f"(type%3ACURRENT_TITLE%2Cvalues%3AList({','.join(title_values)}))")

        # SENIORITY_LEVEL filter (EXCLUDED)
        if request.excludedSeniority:
            seniority_values = []
            for seniority in request.excludedSeniority:
                seniority_id = SENIORITY_IDS.get(seniority, "110")
                encoded_seniority = double_encode(seniority)
                seniority_values.append(f"(id%3A{seniority_id}%2Ctext%3A{encoded_seniority}%2CselectionType%3AEXCLUDED)")
            filters.append(f"(type%3ASENIORITY_LEVEL%2Cvalues%3AList({','.join(seniority_values)}))")

        # REGION filter
        if request.regions:
            region_values = []
            for region in request.regions:
                region_id = REGION_IDS.get(region, "102221843")
                encoded_region = double_encode(region)
                region_values.append(f"(id%3A{region_id}%2Ctext%3A{encoded_region}%2CselectionType%3AINCLUDED)")
            filters.append(f"(type%3AREGION%2Cvalues%3AList({','.join(region_values)}))")

        # COMPANY_HEADQUARTERS filter
        if request.companyHQRegions:
            hq_values = []
            for region in request.companyHQRegions:
                region_id = REGION_IDS.get(region, "102221843")
                encoded_region = double_encode(region)
                hq_values.append(f"(id%3A{region_id}%2Ctext%3A{encoded_region}%2CselectionType%3AINCLUDED)")
            filters.append(f"(type%3ACOMPANY_HEADQUARTERS%2Cvalues%3AList({','.join(hq_values)}))")

        # COMPANY_HEADCOUNT filter
        if request.companyHeadcount:
            headcount_values = []
            for hc in request.companyHeadcount:
                hc_id = HEADCOUNT_IDS.get(hc, "C")
                encoded_hc = double_encode(hc)
                headcount_values.append(f"(id%3A{hc_id}%2Ctext%3A{encoded_hc}%2CselectionType%3AINCLUDED)")
            filters.append(f"(type%3ACOMPANY_HEADCOUNT%2Cvalues%3AList({','.join(headcount_values)}))")

        # FUNCTION filter
        if request.function:
            function_values = []
            for func in request.function:
                func_id = FUNCTION_IDS.get(func, "25")
                encoded_func = double_encode(func)
                function_values.append(f"(id%3A{func_id}%2Ctext%3A{encoded_func}%2CselectionType%3AINCLUDED)")
            filters.append(f"(type%3AFUNCTION%2Cvalues%3AList({','.join(function_values)}))")

        # Build the full query
        filters_str = ",".join(filters)
        query = f"(filters%3AList({filters_str}))"

        # Build full URL
        url = f"https://www.linkedin.com/sales/search/people?query={query}&viewAllFilters=true"

        return {
            "success": True,
            "url": url,
            "orgId": request.orgId,
            "companyName": request.companyName,
            "titles": request.titles,
            "companyHeadcount": request.companyHeadcount,
            "function": request.function,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "orgId": request.orgId,
            "companyName": request.companyName,
        }
