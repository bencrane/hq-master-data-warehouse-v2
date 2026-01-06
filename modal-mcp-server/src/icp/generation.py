"""
ICP Generation Endpoint

Uses OpenAI to generate ICP criteria for target clients.
"""

import os
import json
import modal

from config import app, image


ICP_PROMPT = """You are an expert B2B sales strategist. Given a company, generate ideal customer profile (ICP) criteria for finding leads who would be good prospects for this company's product/service.

Company: {company_name}
Domain: {domain}
LinkedIn: {company_linkedin_url}

Based on what you know about this company, generate ICP criteria in the following JSON format:

{{
  "company_criteria": {{
    "industries": ["list of target industries"],
    "employee_count_min": null or number,
    "employee_count_max": null or number,
    "size": ["list of company size ranges like '51-200 employees'"],
    "countries": ["list of target countries"],
    "founded_min": null or year,
    "founded_max": null or year
  }},
  "person_criteria": {{
    "title_contains_any": ["list of title keywords where at least one must match, e.g. 'VP', 'Director', 'Head of'"],
    "title_contains_all": ["list of title keywords where at least one must match from this list too, e.g. 'Marketing', 'Sales', 'Growth'"]
  }}
}}

Return ONLY the JSON object, no other text.
"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("openai-secret"),
        modal.Secret.from_name("supabase-credentials"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def generate_target_client_icp(request: dict) -> dict:
    """
    Generate ICP criteria for a target client using OpenAI.
    Stores raw response and extracted ICP.
    """
    from openai import OpenAI
    from supabase import create_client

    target_client_id = request.get("target_client_id")
    company_name = request.get("company_name")
    domain = request.get("domain")
    company_linkedin_url = request.get("company_linkedin_url")

    if not target_client_id or not company_name or not domain:
        return {"success": False, "error": "Missing required fields: target_client_id, company_name, domain"}

    openai_api_key = os.environ["OPENAI_API_KEY"]
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]

    client = OpenAI(api_key=openai_api_key)
    supabase = create_client(supabase_url, supabase_key)

    try:
        prompt = ICP_PROMPT.format(
            company_name=company_name,
            domain=domain,
            company_linkedin_url=company_linkedin_url or "N/A",
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a B2B sales strategist. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        raw_response = response.choices[0].message.content.strip()

        if raw_response.startswith("```"):
            lines = raw_response.split("\n")
            raw_response = "\n".join(lines[1:-1])

        icp_data = json.loads(raw_response)

        raw_insert = (
            supabase.schema("raw")
            .from_("icp_payloads")
            .insert({
                "target_client_id": target_client_id,
                "workflow_slug": "ai-generate-target-client-icp",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "raw_payload": icp_data,
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"]

        company_criteria = icp_data.get("company_criteria", {})
        person_criteria = icp_data.get("person_criteria", {})

        extracted_data = {
            "raw_payload_id": raw_id,
            "target_client_id": target_client_id,
            "industries": company_criteria.get("industries"),
            "employee_count_min": company_criteria.get("employee_count_min"),
            "employee_count_max": company_criteria.get("employee_count_max"),
            "size": company_criteria.get("size"),
            "countries": company_criteria.get("countries"),
            "founded_min": company_criteria.get("founded_min"),
            "founded_max": company_criteria.get("founded_max"),
            "title_contains_any": person_criteria.get("title_contains_any"),
            "title_contains_all": person_criteria.get("title_contains_all"),
        }

        extracted_result = (
            supabase.schema("extracted")
            .from_("target_client_icp")
            .upsert(extracted_data, on_conflict="target_client_id")
            .execute()
        )
        extracted_id = extracted_result.data[0]["id"] if extracted_result.data else None

        return {
            "success": True,
            "raw_id": raw_id,
            "extracted_id": extracted_id,
            "icp": icp_data,
        }

    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Failed to parse AI response as JSON: {str(e)}", "raw_response": raw_response}
    except Exception as e:
        return {"success": False, "error": str(e)}
