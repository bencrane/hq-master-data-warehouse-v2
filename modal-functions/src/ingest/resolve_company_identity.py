"""
Resolve Company Identity — Gemini 3 Flash

Takes company name, location, and industry and returns the company domain
and LinkedIn URL using Gemini 3 Flash with web search.

Expects:
{
  "company_name": "Hyundai Motor Company",
  "location": "Seoul, South Korea",  // optional
  "industry": "Motor Vehicle Manufacturing"  // optional
}

Returns:
{
  "success": true,
  "company_name": "Hyundai Motor Company",
  "company_domain": "hyundai.com",
  "company_linkedin_url": "https://www.linkedin.com/company/hyundai",
  "confidence": "high",
  "reasoning": "Found official website and LinkedIn page",
  "input_tokens": 150,
  "output_tokens": 50,
  "cost_usd": 0.00012
}
"""

import os
import json
import modal
from typing import Optional
from pydantic import BaseModel, Field

from config import app, image


class ResolveCompanyIdentityRequest(BaseModel):
    company_name: str = Field(min_length=1)
    location: Optional[str] = None
    industry: Optional[str] = None


PROMPT_TEMPLATE = """Find the official website domain and LinkedIn company page URL for this company.

Company Name: {company_name}
Location: {location}
Industry: {industry}

Search for the company's official website and LinkedIn page. Use the location and industry to disambiguate if there are multiple companies with similar names.

Return ONLY this JSON (no markdown, no explanation):
{{
  "company_domain": "<primary domain like 'example.com' or null if not found>",
  "company_linkedin_url": "<full LinkedIn URL like 'https://www.linkedin.com/company/example' or null if not found>",
  "confidence": "high|medium|low",
  "reasoning": "<brief explanation of how you found these>"
}}

Rules:
- Return the primary/canonical domain (e.g., "hyundai.com" not "hyundai.co.kr")
- LinkedIn URL should be the company page, not a person's profile
- "high" confidence = clear match found with strong evidence
- "medium" confidence = likely correct but some ambiguity
- "low" confidence = best guess, limited evidence
- If you cannot find either, return null for that field"""


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def resolve_company_identity(request: ResolveCompanyIdentityRequest) -> dict:
    """
    Resolve company domain and LinkedIn URL using Gemini 3 Flash.
    """
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    try:
        prompt = PROMPT_TEMPLATE.format(
            company_name=request.company_name,
            location=request.location or "Not specified",
            industry=request.industry or "Not specified",
        )

        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Get token counts
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0

        # Gemini 2.0 Flash pricing: $0.10/MTok input, $0.40/MTok output
        cost_usd = round(
            (input_tokens / 1_000_000 * 0.10) + (output_tokens / 1_000_000 * 0.40),
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
                "error": "Gemini returned unparseable JSON",
                "raw_response": response_text[:500],
                "company_name": request.company_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
            }

        return {
            "success": True,
            "company_name": request.company_name,
            "company_domain": result.get("company_domain"),
            "company_linkedin_url": result.get("company_linkedin_url"),
            "confidence": result.get("confidence"),
            "reasoning": result.get("reasoning"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "company_name": request.company_name,
        }
