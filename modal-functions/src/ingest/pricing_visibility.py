"""
Pricing Visibility Inference

Uses Gemini to analyze a company's pricing page and determine pricing visibility.

Expects:
{
  "company_name": "Example Inc",
  "domain": "example.com",
  "pricing_page_url": "https://example.com/pricing"
}

Returns:
{
  "pricing_visibility": "public" | "hidden" | "partial",
  "explanation": "reason for classification"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_pricing_visibility(request: dict) -> dict:
    import requests
    from bs4 import BeautifulSoup
    import google.generativeai as genai
    from supabase import create_client

    # Setup clients
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        pricing_page_url = request.get("pricing_page_url", "").strip()
        company_name = request.get("company_name", "")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        if not pricing_page_url:
            return {"success": False, "error": "No pricing_page_url provided"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("pricing_visibility_payloads")
            .insert({
                "domain": domain,
                "pricing_page_url": pricing_page_url,
                "company_name": company_name,
                "payload": request,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Fetch pricing page content
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            response = requests.get(pricing_page_url, headers=headers, timeout=15, allow_redirects=True)
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to fetch pricing page: HTTP {response.status_code}",
                    "domain": domain,
                    "raw_payload_id": str(raw_payload_id),
                }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Pricing page fetch timeout", "domain": domain}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Pricing page connection error", "domain": domain}

        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        page_text = soup.get_text(separator=" ", strip=True)
        # Truncate to avoid token limits
        page_text = page_text[:8000]

        # 3. Send to Gemini for classification
        company_context = f"Company: {company_name}" if company_name else f"Domain: {domain}"

        prompt = f"""Analyze this pricing page content and determine pricing visibility.

{company_context}
Pricing Page URL: {pricing_page_url}

Pricing Page Content:
{page_text}

Classify as ONE of:
- public: Full pricing is publicly visible (specific dollar amounts, all tiers shown)
- hidden: No pricing shown, must contact sales or request a quote
- partial: Some pricing shown but not complete (e.g., "starting at $X", only some tiers priced, or "contact us for enterprise")

Respond in this exact JSON format:
{{"pricing_visibility": "public|hidden|partial", "explanation": "1-2 sentence explanation"}}

Only return the JSON, nothing else."""

        model = genai.GenerativeModel("gemini-3-flash-preview")
        gemini_response = model.generate_content(prompt)

        # Parse Gemini response
        import json
        response_text = gemini_response.text.strip()
        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        try:
            result = json.loads(response_text)
            pricing_visibility = result.get("pricing_visibility", "").lower()
            explanation = result.get("explanation", "")
        except json.JSONDecodeError:
            # Fallback parsing
            pricing_visibility = "unknown"
            explanation = response_text
            if "public" in response_text.lower():
                pricing_visibility = "public"
            elif "hidden" in response_text.lower():
                pricing_visibility = "hidden"
            elif "partial" in response_text.lower():
                pricing_visibility = "partial"

        # Validate value
        if pricing_visibility not in ["public", "hidden", "partial"]:
            pricing_visibility = "unknown"

        # 4. Insert into extracted
        supabase.schema("extracted").from_("company_pricing_visibility").insert({
            "raw_payload_id": raw_payload_id,
            "domain": domain,
            "pricing_page_url": pricing_page_url,
            "pricing_visibility": pricing_visibility,
            "explanation": explanation,
        }).execute()

        # 5. Upsert into core
        supabase.schema("core").from_("company_pricing_visibility").upsert({
            "domain": domain,
            "pricing_visibility": pricing_visibility,
            "explanation": explanation,
            "last_checked_at": "now()",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "pricing_visibility": pricing_visibility,
            "explanation": explanation,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
