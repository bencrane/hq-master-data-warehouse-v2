"""
Discover G2 Page URL using Gemini

Uses Gemini to search for and find a company's G2.com product page URL.

Expects:
{
  "domain": "example.com",
  "company_name": "Example Inc"
}

Returns:
{
  "success": true,
  "domain": "example.com",
  "g2_url": "https://www.g2.com/products/example"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def discover_g2_page_gemini(request: dict) -> dict:
    import google.generativeai as genai
    import re

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    try:
        domain = request.get("domain", "").lower().strip()
        company_name = request.get("company_name", "").strip()

        if not domain:
            return {"success": False, "error": "No domain provided"}

        if not company_name:
            return {"success": False, "error": "No company_name provided"}

        # Build prompt for Gemini
        prompt = f"""Find the G2.com product page URL for {company_name} (website: {domain}).

G2.com is a software review platform. Companies have product pages at URLs like:
- https://www.g2.com/products/slack
- https://www.g2.com/products/salesforce-sales-cloud
- https://www.g2.com/products/hubspot-marketing-hub

Search your knowledge for the G2 product page URL for {company_name}.

If you know the URL, respond with ONLY the URL, nothing else.
If you don't know or can't find it, respond with: NOT_FOUND

Example good response: https://www.g2.com/products/stripe
Example not found response: NOT_FOUND"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        gemini_response = model.generate_content(prompt)

        response_text = gemini_response.text.strip()

        # Extract G2 URL from response
        g2_url = None
        if response_text != "NOT_FOUND":
            g2_match = re.search(r'https?://(?:www\.)?g2\.com/products/[^\s\'"<>]+', response_text)
            if g2_match:
                g2_url = g2_match.group(0).rstrip('.,;:)')

        return {
            "success": True,
            "domain": domain,
            "company_name": company_name,
            "g2_url": g2_url,
            "raw_response": response_text[:500] if response_text else None
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
