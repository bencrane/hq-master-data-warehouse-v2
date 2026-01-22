"""
Company Address Parsing

Ingest endpoint that receives company records, calls AI to parse the
"Company registered address" field into structured components (city, state, country),
then stores raw payload and extracted data.

Workflow: ai-company-address-parsing
Input: Single company record with address
Output: Parsed address components
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.company_address import extract_company_address


# System prompt for address parsing
ADDRESS_PARSING_PROMPT = """#CONTEXT#

You are an information extraction system. You will be given a single free-text location string that may represent a city, a state/region, a country, or some combination of those. Your job is to parse the string and extract only what is explicitly present, without inferring missing components.

#OBJECTIVE#

Parse the input location string and return structured fields: city, state, country, hasCity, hasState, hasCountry.

#INSTRUCTIONS#

- Extract explicitly stated components only. Do not infer or guess missing information from context or common knowledge.

- Normalize whitespace and punctuation; handle duplicates and metropolitan area formats conservatively (e.g., "Seattle, WA, USA", "Paris, Île-de-France, France", "NYC, New York", "San Francisco Bay Area, California").

- If a component (city/state/country) is clearly present, return its value; otherwise return null for that component.

- Set booleans strictly based on presence: hasCity, hasState, hasCountry should be true only if that component is explicitly present in the input.

- Prefer the most specific explicit token for city (e.g., for "San Francisco Bay Area", city = "San Francisco Bay Area"; do not reduce to "San Francisco" unless explicitly written). For metro areas like "Greater London", treat as city if that is how it appears.

- For state/region, preserve the explicit form as written (e.g., "CA", "California", "Île-de-France", "Bavaria"). Do not expand abbreviations.

- For country, preserve the explicit form as written (e.g., "USA", "United States", "UK", "United Kingdom"). Do not standardize or expand.

- Be conservative with ambiguous tokens (e.g., "Georgia" could be a country or a state). If ambiguity exists and no other disambiguating tokens are present, assign it to the component that is explicitly indicated by formatting or context words; otherwise leave uncertain components as null and only set the boolean for the clearly indicated component. Do not infer.

- If the input is empty or contains no location content, return null for all three components and set all booleans to false.

- Output must be a single JSON object with camelCase keys: city, state, country, hasCity, hasState, hasCountry.

#EXAMPLES#

Input: "Seattle, WA, USA"
Output: {"city":"Seattle","state":"WA","country":"USA","hasCity":true,"hasState":true,"hasCountry":true}

Input: "Paris, Île-de-France, France"
Output: {"city":"Paris","state":"Île-de-France","country":"France","hasCity":true,"hasState":true,"hasCountry":true}

Input: "San Francisco Bay Area, California"
Output: {"city":"San Francisco Bay Area","state":"California","country":null,"hasCity":true,"hasState":true,"hasCountry":false}

Input: "New York, USA"
Output: {"city":"New York","state":null,"country":"USA","hasCity":true,"hasState":false,"hasCountry":true}

Input: "California"
Output: {"city":null,"state":"California","country":null,"hasCity":false,"hasState":true,"hasCountry":false}

Input: "United Kingdom"
Output: {"city":null,"state":null,"country":"United Kingdom","hasCity":false,"hasState":false,"hasCountry":true}

Input: "Greater London, United Kingdom"
Output: {"city":"Greater London","state":null,"country":"United Kingdom","hasCity":true,"hasState":false,"hasCountry":true}

Input: "Georgia"
Output: {"city":null,"state":null,"country":null,"hasCity":false,"hasState":false,"hasCountry":false}

Input: ""
Output: {"city":null,"state":null,"country":null,"hasCity":false,"hasState":false,"hasCountry":false}"""


class CompanyAddressRequest(BaseModel):
    """Request model for company address parsing."""
    
    # Company fields (snake_case)
    company_name: Optional[str] = None
    linkedin_url: Optional[str] = None
    linkedin_urn: Optional[str] = None
    domain: Optional[str] = None  # Pre-normalized domain (not URL)
    company_description: Optional[str] = None
    company_headcount: Optional[str] = None  # String, will parse to int
    company_industries: Optional[str] = None
    company_registered_address: Optional[str] = None
    
    # Workflow metadata
    workflow_slug: str = "ai-company-address-parsing"


def parse_address_with_gemini(address: str) -> dict:
    """Call Gemini to parse the address string."""
    import google.generativeai as genai
    
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    prompt = f'{ADDRESS_PARSING_PROMPT}\n\nInput: "{address}"'
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    
    return json.loads(response.text)


def parse_headcount(headcount_str: Optional[str]) -> Optional[int]:
    """Parse headcount string to integer, handling various formats."""
    if not headcount_str:
        return None
    
    try:
        # Remove commas and try to parse
        cleaned = headcount_str.replace(",", "").strip()
        return int(cleaned)
    except (ValueError, AttributeError):
        return None


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_company_address_parsing(request: CompanyAddressRequest) -> dict:
    """
    Ingest company record, parse address with AI, store raw + extracted.
    
    Flow:
    1. Store raw payload (original input)
    2. Call Gemini to parse the address
    3. Store extracted data (with AI-parsed fields)
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Parse headcount to int
        headcount = parse_headcount(request.company_headcount)
        
        # Build the raw payload (original data as received)
        raw_payload = {
            "company_name": request.company_name,
            "linkedin_urn": request.linkedin_urn,
            "linkedin_url": request.linkedin_url,
            "domain": request.domain,
            "company_description": request.company_description,
            "company_headcount": request.company_headcount,
            "company_industries": request.company_industries,
            "company_registered_address": request.company_registered_address,
        }
        
        # 1. Store raw payload FIRST (before AI processing)
        raw_record = {
            "company_name": request.company_name,
            "linkedin_url": request.linkedin_url,
            "linkedin_urn": request.linkedin_urn,
            "domain": request.domain,
            "raw_payload": raw_payload,
            "workflow_slug": request.workflow_slug,
        }
        
        raw_result = (
            supabase.schema("raw")
            .from_("salesnav_scrapes_company_address_payloads")
            .insert(raw_record)
            .execute()
        )
        
        if not raw_result.data:
            return {"success": False, "error": "Failed to insert raw payload"}
        
        raw_payload_id = raw_result.data[0]["id"]
        
        # 2. Call AI to parse the address
        address_to_parse = request.company_registered_address or ""
        ai_response = parse_address_with_gemini(address_to_parse)
        
        # Extract parsed address components from AI response
        city = ai_response.get("city")
        state = ai_response.get("state")
        country = ai_response.get("country")
        has_city = ai_response.get("hasCity", False)
        has_state = ai_response.get("hasState", False)
        has_country = ai_response.get("hasCountry", False)
        
        # 3. Store extracted data (with AI-parsed fields)
        extraction_result = extract_company_address(
            supabase=supabase,
            raw_payload_id=raw_payload_id,
            company_name=request.company_name,
            linkedin_url=request.linkedin_url,
            linkedin_urn=request.linkedin_urn,
            domain=request.domain,
            description=request.company_description,
            headcount=headcount,
            industries=request.company_industries,
            registered_address_raw=request.company_registered_address,
            city=city,
            state=state,
            country=country,
            has_city=has_city,
            has_state=has_state,
            has_country=has_country,
        )
        
        return {
            "success": True,
            "raw_id": raw_payload_id,
            "extracted_id": extraction_result.get("extracted_id"),
            "company_name": request.company_name,
            "domain": request.domain,
            "parsed_address": {
                "city": city,
                "state": state,
                "country": country,
                "has_city": has_city,
                "has_state": has_state,
                "has_country": has_country,
            },
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
