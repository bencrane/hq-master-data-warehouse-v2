"""
LinkedIn URL Inference

Uses Gemini to infer company LinkedIn URL from name and domain.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional

from config import app, image


class LinkedInUrlInferenceRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_company_linkedin_url(request: LinkedInUrlInferenceRequest) -> dict:
    """
    Infer company LinkedIn URL using Gemini.
    """
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    try:
        # Build prompt for Gemini
        prompt = f"""Given the following company information, return the most likely LinkedIn company page URL.

Company Name: {request.company_name}
Domain: {request.domain or 'N/A'}

Return ONLY the full LinkedIn URL in the format: https://www.linkedin.com/company/[company-slug]
If you cannot determine the LinkedIn URL, return "Unknown".
Do not include any other text.
"""

        # Call Gemini
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)

        # Extract token usage and calculate cost
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 3 Flash pricing estimate
        cost_usd = (input_tokens * 0.10 / 1_000_000) + (output_tokens * 0.40 / 1_000_000)

        linkedin_url = response.text.strip()

        # Validate it looks like a LinkedIn URL
        if not linkedin_url.startswith("https://www.linkedin.com/company/") and not linkedin_url.startswith("https://linkedin.com/company/"):
            linkedin_url = None

        return {
            "success": True,
            "company_name": request.company_name,
            "linkedin_url": linkedin_url,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
