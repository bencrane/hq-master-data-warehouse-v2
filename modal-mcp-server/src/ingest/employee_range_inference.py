"""
Employee Range Inference

Uses Gemini to infer company employee range from name, domain, and linkedin_url.
Classifies into one of our standard ranges.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image

# Standard employee ranges
EMPLOYEE_RANGES = [
    "1-10",
    "11-50",
    "51-100",
    "101-250",
    "251-500",
    "501-1000",
    "1001-5000",
    "5001-10000",
    "10001+",
]


class EmployeeRangeInferenceRequest(BaseModel):
    company_name: str
    domain: str
    company_linkedin_url: Optional[str] = None


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_company_employee_range(request: EmployeeRangeInferenceRequest) -> dict:
    """
    Infer company employee range using Gemini.
    """
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    try:
        ranges_str = ", ".join(EMPLOYEE_RANGES)

        # Build prompt for Gemini
        prompt = f"""Given the following company information, estimate the employee count and classify it into one of these ranges:
{ranges_str}

Company Name: {request.company_name}
Domain: {request.domain or 'N/A'}
LinkedIn URL: {request.company_linkedin_url or 'N/A'}

Return ONLY one of the exact ranges listed above (e.g., "51-100" or "1001-5000"). If you cannot determine, return "Unknown".
"""

        # Call Gemini
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)

        # Extract token usage and calculate cost
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 2.5 Flash pricing (estimate): $0.15/1M input, $0.60/1M output
        cost_usd = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)

        employee_range = response.text.strip()

        # Validate it's one of our ranges
        if employee_range not in EMPLOYEE_RANGES:
            employee_range = None

        return {
            "success": True,
            "company_name": request.company_name,
            "employee_range": employee_range,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
