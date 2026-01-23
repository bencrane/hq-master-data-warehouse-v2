"""
SalesNav Person Ingestion Endpoint

Ingests person data from SalesNav scrapes with AI-powered location parsing.
Flow: raw -> AI (Gemini location parsing) -> extracted
"""

import os
import re
import json
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image
from extraction.salesnav_person import extract_salesnav_person


# Location parsing prompt - strips "Greater", "Metro", "Area" etc. for clean city names
LOCATION_PARSING_PROMPT = """#CONTEXT#

You are an information extraction system. You will be given a single free-text location string that may represent a city, a state/region, a country, or some combination of those. Your job is to parse the string and extract only what is explicitly present, without inferring missing components.

#OBJECTIVE#

Parse the input location string and return structured fields: city, state, country, hasCity, hasState, hasCountry.

#INSTRUCTIONS#

- Extract explicitly stated components only. Do not infer or guess missing information from context or common knowledge.
- Normalize whitespace and punctuation; handle duplicates and metropolitan area formats conservatively.
- If a component (city/state/country) is clearly present, return its value; otherwise return null for that component.
- Set booleans strictly based on presence: hasCity, hasState, hasCountry should be true only if that component is explicitly present in the input.
- IMPORTANT: For city names, aggressively strip prefixes/suffixes like "Greater", "Metro", "Metropolitan", "Area", "Bay Area", "Region". Examples:
  - "Greater Cleveland" -> city = "Cleveland"
  - "San Francisco Bay Area" -> city = "San Francisco"
  - "Greater London" -> city = "London"
  - "New York City Metropolitan Area" -> city = "New York City"
  - "Dallas-Fort Worth Metroplex" -> city = "Dallas-Fort Worth"
- For state/region, preserve the explicit form as written (e.g., "CA", "California", "Île-de-France", "Bavaria"). Do not expand abbreviations.
- For country, preserve the explicit form as written (e.g., "USA", "United States", "UK", "United Kingdom"). Do not standardize or expand.
- Be conservative with ambiguous tokens (e.g., "Georgia" could be a country or a state). If ambiguity exists and no other disambiguating tokens are present, assign it to the component that is explicitly indicated by formatting or context words; otherwise leave uncertain components as null and only set the boolean for the clearly indicated component. Do not infer.
- If the input is empty or contains no location content, return null for all three components and set all booleans to false.
- Output must be a single JSON object with camelCase keys: city, state, country, hasCity, hasState, hasCountry.

#EXAMPLES#

Input: "Seattle, WA, USA"
Output: {"city":"Seattle","state":"WA","country":"USA","hasCity":true,"hasState":true,"hasCountry":true}

Input: "Greater Cleveland, Ohio"
Output: {"city":"Cleveland","state":"Ohio","country":null,"hasCity":true,"hasState":true,"hasCountry":false}

Input: "San Francisco Bay Area, California"
Output: {"city":"San Francisco","state":"California","country":null,"hasCity":true,"hasState":true,"hasCountry":false}

Input: "New York City Metropolitan Area, USA"
Output: {"city":"New York City","state":null,"country":"USA","hasCity":true,"hasState":false,"hasCountry":true}

Input: "Greater London, United Kingdom"
Output: {"city":"London","state":null,"country":"United Kingdom","hasCity":true,"hasState":false,"hasCountry":true}

Input: "California"
Output: {"city":null,"state":"California","country":null,"hasCity":false,"hasState":true,"hasCountry":false}

Input: "United Kingdom"
Output: {"city":null,"state":null,"country":"United Kingdom","hasCity":false,"hasState":false,"hasCountry":true}

Input: "Georgia"
Output: {"city":null,"state":null,"country":null,"hasCity":false,"hasState":false,"hasCountry":false}

Input: ""
Output: {"city":null,"state":null,"country":null,"hasCity":false,"hasState":false,"hasCountry":false}

Now parse this location:
"""


class SalesNavPersonRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    profile_headline: Optional[str] = None
    profile_summary: Optional[str] = None
    job_title: Optional[str] = None
    job_description: Optional[str] = None
    job_started_on: Optional[str] = None
    person_linkedin_sales_nav_url: Optional[str] = None
    linkedin_user_profile_urn: Optional[str] = None
    location: Optional[str] = None
    company_name: Optional[str] = None
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None
    source_id: Optional[str] = None
    upload_id: Optional[str] = None
    notes: Optional[str] = None
    matching_filters: Optional[str] = None
    source_created_at: Optional[str] = None
    clay_batch_number: Optional[str] = None
    sent_to_clay_at: Optional[str] = None
    export_title: Optional[str] = None
    export_timestamp: Optional[str] = None


def parse_location_with_gemini(location: str) -> dict:
    """
    Parse location string using Gemini 2.0 Flash.
    Returns dict with city, state, country, hasCity, hasState, hasCountry.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {
            "city": None, "state": None, "country": None,
            "hasCity": False, "hasState": False, "hasCountry": False
        }

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = LOCATION_PARSING_PROMPT + f'"{location}"'

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean markdown code blocks if present
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n?", "", response_text)
            response_text = re.sub(r"\n?```$", "", response_text)

        return json.loads(response_text)
    except Exception as e:
        print(f"Gemini parsing error: {e}")
        return {
            "city": None, "state": None, "country": None,
            "hasCity": False, "hasState": False, "hasCountry": False
        }


def clean_name(name: Optional[str]) -> Optional[str]:
    """
    Clean name by removing emojis and decorative characters.
    """
    if not name:
        return name

    # Remove emojis and special unicode characters
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols extended
        "\U00002600-\U000026FF"  # misc symbols
        "\U00002700-\U000027BF"  # dingbats
        "]+",
        flags=re.UNICODE
    )

    cleaned = emoji_pattern.sub("", name)
    # Clean up extra whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned.strip() if cleaned.strip() else name


def normalize_null_string(value: Optional[str]) -> Optional[str]:
    """Convert string 'null' to actual None."""
    if value is None or value == "null" or value == "":
        return None
    return value


def parse_boolean_string(value: Optional[str]) -> Optional[bool]:
    """Parse boolean from string."""
    if value is None or value == "null" or value == "":
        return None
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "yes")


def parse_timestamp(value: Optional[str]) -> Optional[str]:
    """Parse and validate timestamp string."""
    if value is None or value == "null" or value == "":
        return None
    return value


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-api-key"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def ingest_salesnav_scrapes_person(request: SalesNavPersonRequest) -> dict:
    """
    Ingest SalesNav person data with AI location parsing.
    Flow: raw -> AI (Gemini) -> extracted
    """
    from supabase import create_client

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build raw payload from request
        raw_payload = request.model_dump()

        # 1. Store raw payload first
        raw_insert = (
            supabase.schema("raw")
            .from_("salesnav_scrapes_person_payloads")
            .insert({
                "person_linkedin_sales_nav_url": request.person_linkedin_sales_nav_url,
                "linkedin_user_profile_urn": request.linkedin_user_profile_urn,
                "domain": request.domain,
                "raw_payload": raw_payload,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        # 2. Parse location with Gemini
        location_raw = normalize_null_string(request.location)
        parsed_location = {
            "city": None, "state": None, "country": None,
            "hasCity": False, "hasState": False, "hasCountry": False
        }

        if location_raw:
            parsed_location = parse_location_with_gemini(location_raw)

        # 3. Clean names (remove emojis)
        first_name = clean_name(normalize_null_string(request.first_name))
        last_name = clean_name(normalize_null_string(request.last_name))

        # 4. Extract to extracted table
        extracted_result = extract_salesnav_person(
            supabase=supabase,
            raw_payload_id=raw_id,
            first_name=first_name,
            last_name=last_name,
            email=normalize_null_string(request.email),
            phone_number=normalize_null_string(request.phone_number),
            profile_headline=normalize_null_string(request.profile_headline),
            profile_summary=normalize_null_string(request.profile_summary),
            job_title=normalize_null_string(request.job_title),
            job_description=normalize_null_string(request.job_description),
            job_started_on=normalize_null_string(request.job_started_on),
            person_linkedin_sales_nav_url=normalize_null_string(request.person_linkedin_sales_nav_url),
            linkedin_user_profile_urn=normalize_null_string(request.linkedin_user_profile_urn),
            location_raw=location_raw,
            city=parsed_location.get("city"),
            state=parsed_location.get("state"),
            country=parsed_location.get("country"),
            has_city=parsed_location.get("hasCity", False),
            has_state=parsed_location.get("hasState", False),
            has_country=parsed_location.get("hasCountry", False),
            company_name=normalize_null_string(request.company_name),
            domain=normalize_null_string(request.domain),
            company_linkedin_url=normalize_null_string(request.company_linkedin_url),
            source_id=normalize_null_string(request.source_id),
            upload_id=normalize_null_string(request.upload_id),
            notes=normalize_null_string(request.notes),
            matching_filters=parse_boolean_string(request.matching_filters),
            source_created_at=parse_timestamp(request.source_created_at),
            clay_batch_number=normalize_null_string(request.clay_batch_number),
            sent_to_clay_at=parse_timestamp(request.sent_to_clay_at),
            export_title=normalize_null_string(request.export_title),
            export_timestamp=normalize_null_string(request.export_timestamp),
        )

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_result["id"] if extracted_result else None,
            "parsed_location": parsed_location,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
