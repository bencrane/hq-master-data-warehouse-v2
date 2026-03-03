"""
SalesNav URL Constructor

Takes structured inputs and outputs a fully encoded LinkedIn Sales Navigator
search URL ready to be sent to the RapidAPI scraper endpoint.

Uses Claude Haiku 4.5 to pattern-match the double-encoding from a working example.
Spaces become %2520, colons become %253A, etc.
"""

import os
import modal
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
    companyHeadcount: Optional[List[str]] = Field(default=None, description="Company headcount ranges (e.g. '11-50', '51-200', '201-500', '501-1000', '1001-5000', '5001-10,000', '10,000+')")
    function: Optional[List[str]] = Field(default=None, description="Job functions (e.g. 'Sales', 'Engineering')")


PROMPT_TEMPLATE = """Here is an exact working LinkedIn Sales Navigator search URL:

https://www.linkedin.com/sales/search/people?query=(recentSearchParam%3A(id%3A5287348538%2CdoLogHistory%3Atrue)%2Cfilters%3AList((type%3APAST_COMPANY%2Cvalues%3AList((id%3Aurn%253Ali%253Aorganization%253A3185%2Ctext%3ASalesforce%2CselectionType%3AINCLUDED%2Cparent%3A(id%3A0))))%2C(type%3ACURRENT_COMPANY%2Cvalues%3AList((id%3Aurn%253Ali%253Aorganization%253A3185%2Ctext%3ASalesforce%2CselectionType%3AEXCLUDED%2Cparent%3A(id%3A0))))%2C(type%3AFUNCTION%2Cvalues%3AList((id%3A25%2Ctext%3ASales%2CselectionType%3AINCLUDED)))%2C(type%3ASENIORITY_LEVEL%2Cvalues%3AList((id%3A110%2Ctext%3AEntry%2520Level%2CselectionType%3AEXCLUDED)))%2C(type%3ACURRENT_TITLE%2Cvalues%3AList((text%3AVP%2520Sales%2CselectionType%3AINCLUDED)%2C(text%3AHead%2520Sales%2CselectionType%3AINCLUDED)))%2C(type%3ACOMPANY_HEADCOUNT%2Cvalues%3AList((id%3AC%2Ctext%3A11-50%2CselectionType%3AINCLUDED)%2C(id%3AE%2Ctext%3A201-500%2CselectionType%3AINCLUDED)%2C(id%3AG%2Ctext%3A1001-5000%2CselectionType%3AINCLUDED)%2C(id%3AF%2Ctext%3A501-1000%2CselectionType%3AINCLUDED)%2C(id%3AH%2Ctext%3A5001-10%252C000%2CselectionType%3AINCLUDED)%2C(id%3AI%2Ctext%3A10%252C000%252B%2CselectionType%3AINCLUDED)%2C(id%3AD%2Ctext%3A51-200%2CselectionType%3AINCLUDED)))%2C(type%3AREGION%2Cvalues%3AList((id%3A102221843%2Ctext%3ANorth%2520America%2CselectionType%3AINCLUDED)))%2C(type%3AINDUSTRY%2Cvalues%3AList((id%3A4%2Ctext%3ASoftware%2520Development%2CselectionType%3AINCLUDED)))%2C(type%3ACOMPANY_HEADQUARTERS%2Cvalues%3AList((id%3A102221843%2Ctext%3ANorth%2520America%2CselectionType%3AINCLUDED)))))&sessionId=XduJs1YOTWiwPjuc%2F7Imqg%3D%3D&viewAllFilters=true

Construct a new Sales Navigator search URL using the inputs below. Match the exact encoding pattern from the example — spaces become %2520, colons in URNs become %253A, commas become %2C, parentheses become %28 and %29.

Inputs:
- orgId: {orgId}
- companyName: {companyName}
- titles: {titles}
- excludedSeniority: {excludedSeniority}
- regions: {regions}
- companyHQRegions: {companyHQRegions}
- companyHeadcount: {companyHeadcount}
- function: {function}

Build the URL with these filters:
- PAST_COMPANY: orgId + companyName, selectionType INCLUDED
- CURRENT_COMPANY: same orgId + companyName, selectionType EXCLUDED
- CURRENT_TITLE: one entry per title, all selectionType INCLUDED
- SENIORITY_LEVEL: one entry per excludedSeniority value, all selectionType EXCLUDED
- REGION: one entry per region, all selectionType INCLUDED
- COMPANY_HEADQUARTERS: one entry per companyHQRegion, all selectionType INCLUDED
- COMPANY_HEADCOUNT: if companyHeadcount provided, one entry per range. Map ranges to IDs: B=1-10, C=11-50, D=51-200, E=201-500, F=501-1000, G=1001-5000, H=5001-10,000, I=10,000+. All selectionType INCLUDED.
- FUNCTION: if function provided, one entry per function. Common IDs: 1=Accounting, 2=Administrative, 3=Arts and Design, 4=Business Development, 5=Community & Social Services, 6=Consulting, 7=Education, 8=Engineering, 9=Entrepreneurship, 10=Finance, 11=Healthcare Services, 12=Human Resources, 13=Information Technology, 14=Legal, 15=Marketing, 16=Media & Communications, 17=Military & Protective Services, 18=Operations, 19=Product Management, 20=Program & Project Management, 21=Purchasing, 22=Quality Assurance, 23=Real Estate, 24=Research, 25=Sales, 26=Support. All selectionType INCLUDED.

Do NOT include INDUSTRY filter.

Return only the URL. Nothing else."""


@app.function(
    image=image,
    timeout=300,
    secrets=[
        modal.Secret.from_name("anthropic-api"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def build_salesnav_url(request: BuildSalesNavURLRequest) -> dict:
    """
    Construct a LinkedIn Sales Navigator search URL using Claude Haiku.
    Pattern-matches double-encoding from a working example.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    try:
        # Build the prompt with inputs
        prompt = PROMPT_TEMPLATE.format(
            orgId=request.orgId,
            companyName=request.companyName,
            titles=", ".join(request.titles),
            excludedSeniority=", ".join(request.excludedSeniority or ["Entry Level"]),
            regions=", ".join(request.regions or ["North America"]),
            companyHQRegions=", ".join(request.companyHQRegions or ["North America"]),
            companyHeadcount=", ".join(request.companyHeadcount) if request.companyHeadcount else "None",
            function=", ".join(request.function) if request.function else "None",
        )

        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            temperature=0,
            messages=[
                {"role": "user", "content": prompt},
            ],
        )

        response_text = message.content[0].text.strip()
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        # Cost: Claude 3 Haiku = $0.25/MTok input, $1.25/MTok output
        cost_usd = round(
            (input_tokens / 1_000_000 * 0.25) + (output_tokens / 1_000_000 * 1.25),
            6,
        )

        # Validate it looks like a URL
        if not response_text.startswith("https://www.linkedin.com/sales/search/people"):
            return {
                "success": False,
                "error": "Response does not look like a valid Sales Navigator URL",
                "raw_response": response_text[:500],
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost_usd,
                },
            }

        return {
            "success": True,
            "url": response_text,
            "orgId": request.orgId,
            "companyName": request.companyName,
            "titles": request.titles,
            "companyHeadcount": request.companyHeadcount,
            "function": request.function,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "orgId": request.orgId,
            "companyName": request.companyName,
        }
