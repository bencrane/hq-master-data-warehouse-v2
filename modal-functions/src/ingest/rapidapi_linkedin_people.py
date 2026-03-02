"""
RapidAPI LinkedIn People Search — Claude Haiku Extraction

Takes a RapidAPI LinkedIn people search response and extracts/normalizes
the person data via Claude Haiku 3.5.

Expects:
{
  "company_domain": "hyundai.com",
  "rapidapi_response": { ... }  // Full RapidAPI response object
}

Returns:
{
  "success": true,
  "company_domain": "hyundai.com",
  "people": [...],
  "people_count": 11,
  "usage": {"input_tokens": 1234, "output_tokens": 567, "cost_usd": 0.00123}
}
"""

import os
import json
import modal
from config import app, image


SYSTEM_PROMPT = """You are a JSON extractor. You will receive a RapidAPI LinkedIn people search response containing employee profiles from a company search.

Your job: extract and normalize every person into a clean, consistent schema.

OUTPUT SCHEMA (respond with ONLY this JSON, no markdown, no explanation):
{
  "company_domain": "<domain provided in context>",
  "people": [
    {
      "first_name": "<firstName>",
      "last_name": "<lastName>",
      "full_name": "<fullName>",
      "geo_region": "<geoRegion>",
      "linkedin_url": "<navigationUrl>",
      "linkedin_urn": "<profileUrn>",
      "profile_picture_url": "<profilePictureDisplayImage or null>",
      "summary": "<summary or null>",
      "open_link": <boolean>,
      "current_position": {
        "title": "<title>",
        "company_name": "<companyName>",
        "company_id": "<companyId>",
        "description": "<description or null>",
        "is_current": <boolean>,
        "start_month": <month or null>,
        "start_year": <year or null>,
        "tenure_years": <numYears or null>,
        "tenure_months": <numMonths or null>,
        "company_tenure_years": <tenureAtCompany.numYears or null>,
        "company_tenure_months": <tenureAtCompany.numMonths or null>,
        "company_industry": "<companyUrnResolutionResult.industry or null>",
        "company_location": "<companyUrnResolutionResult.location or null>",
        "company_logo_url": "<companyUrnResolutionResult.companyPictureDisplayImage or null>"
      }
    }
  ],
  "people_count": <integer count of people extracted>,
  "pagination": {
    "total": <total from response>,
    "count": <count from response>,
    "start": <start from response>
  }
}

RULES:
- Extract ALL people from response.data array
- Convert camelCase field names to snake_case
- If a field is missing or empty, use null
- Preserve exact string values — do not modify or normalize them
- For tenure fields, extract numYears and numMonths separately
- If tenureAtPosition or tenureAtCompany is empty object {}, set those fields to null
- Extract company metadata from companyUrnResolutionResult when available"""


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("anthropic-api"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def rapidapi_linkedin_people(request: dict) -> dict:
    import anthropic
    from supabase import create_client

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    try:
        company_domain = request.get("company_domain", "").strip()
        rapidapi_response = request.get("rapidapi_response")

        if not company_domain:
            return {"success": False, "error": "company_domain is required"}
        if not rapidapi_response:
            return {"success": False, "error": "rapidapi_response is required"}

        # Validate the response structure
        if not isinstance(rapidapi_response, dict):
            return {"success": False, "error": "rapidapi_response must be a JSON object"}

        response_data = rapidapi_response.get("response", {})
        people_data = response_data.get("data", [])

        if not people_data:
            return {
                "success": True,
                "company_domain": company_domain,
                "people": [],
                "people_count": 0,
                "message": "No people found in response",
            }

        # Prepare input for Claude
        claude_input = {
            "company_domain": company_domain,
            "response": response_data,
        }

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=8192,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": json.dumps(claude_input, ensure_ascii=False)},
            ],
        )

        response_text = message.content[0].text.strip()
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens

        # Cost: Haiku 4.5 = $0.80/MTok input, $4.00/MTok output
        cost_usd = round(
            (input_tokens / 1_000_000 * 0.80) + (output_tokens / 1_000_000 * 4.00),
            6,
        )

        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Claude returned unparseable JSON",
                "raw_response": response_text[:2000],
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost_usd": cost_usd,
                },
            }

        people = result.get("people", [])
        people_count = result.get("people_count", len(people))
        pagination = result.get("pagination", {})

        # Store in Supabase
        supabase_url = os.environ["SUPABASE_URL"]
        supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
        supabase = create_client(supabase_url, supabase_key)

        # Insert raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("rapidapi_linkedin_people")
            .insert({
                "company_domain": company_domain,
                "raw_payload": rapidapi_response,
                "cost_usd": cost_usd,
            })
            .execute()
        )

        raw_id = raw_insert.data[0]["id"] if raw_insert.data else None

        # Insert extracted people
        for person in people:
            supabase.schema("extracted").from_("rapidapi_linkedin_people").insert({
                "raw_id": raw_id,
                "company_domain": company_domain,
                "first_name": person.get("first_name"),
                "last_name": person.get("last_name"),
                "full_name": person.get("full_name"),
                "geo_region": person.get("geo_region"),
                "linkedin_url": person.get("linkedin_url"),
                "linkedin_urn": person.get("linkedin_urn"),
                "profile_picture_url": person.get("profile_picture_url"),
                "summary": person.get("summary"),
                "open_link": person.get("open_link"),
                "current_position": person.get("current_position"),
            }).execute()

        return {
            "success": True,
            "company_domain": company_domain,
            "people": people,
            "people_count": people_count,
            "pagination": pagination,
            "raw_id": raw_id,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost_usd,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "company_domain": request.get("company_domain", "unknown"),
        }
