"""
Location Inference

Uses Gemini to infer company headquarters location (city, state, country) from name, domain, and linkedin_url.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class CountryInferenceRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    company_linkedin_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_company_country(request: CountryInferenceRequest) -> dict:
    """
    Infer company headquarters country using Gemini.
    """
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    try:
        # Build prompt for Gemini
        prompt = f"""Given the following company information, return the headquarters location.

Company Name: {request.company_name}
Domain: {request.domain or 'N/A'}
LinkedIn URL: {request.company_linkedin_url or 'N/A'}

Return a JSON object with city, state, and country fields. Use null for any field you cannot determine.
Example: {{"city": "San Francisco", "state": "California", "country": "United States"}}
Example: {{"city": "London", "state": null, "country": "United Kingdom"}}

Return ONLY the JSON object, no other text.
"""

        # Call Gemini
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)

        # Extract token usage and calculate cost
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 2.0 Flash pricing: $0.10/1M input, $0.40/1M output
        cost_usd = (input_tokens * 0.10 / 1_000_000) + (output_tokens * 0.40 / 1_000_000)

        # Parse JSON response
        import json
        raw_text = response.text.strip()
        # Strip markdown code blocks if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        location = json.loads(raw_text)

        return {
            "success": True,
            "company_name": request.company_name,
            "city": location.get("city"),
            "state": location.get("state"),
            "country": location.get("country"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
