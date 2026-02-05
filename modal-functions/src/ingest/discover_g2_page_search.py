"""
Discover G2 Page URL using Gemini with Search

Uses Gemini to search for and find a company's G2.com page URL.

Expects:
{
  "domain": "example.com",
  "company_name": "Example Inc"
}

Returns:
{
  "success": true,
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
def discover_g2_page_gemini_search(request: dict) -> dict:
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

        prompt = f"""Search for the G2.com page for {company_name} (website: {domain}).

G2.com is a software review platform. Company pages can be at URLs like:
- https://www.g2.com/products/slack
- https://www.g2.com/sellers/palo-alto-networks
- https://www.g2.com/products/hubspot-marketing-hub

DO NOT guess or interpolate the URL. Only return a URL if you can actually find/verify it exists.

If you find the G2 page, return ONLY the full URL.
If you cannot find it, return exactly: NOT_FOUND"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)

        response_text = response.text.strip()

        g2_url = None
        if response_text != "NOT_FOUND":
            g2_match = re.search(r'https?://(?:www\.)?g2\.com/(?:products|sellers|vendors)/[^\s\'"<>]+', response_text)
            if g2_match:
                g2_url = g2_match.group(0).rstrip('.,;:)')

        return {
            "success": True,
            "domain": domain,
            "company_name": company_name,
            "g2_url": g2_url
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
