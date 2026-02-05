"""
Discover Pricing Page URL

Uses Gemini to analyze a company's website and find the pricing page URL.

Expects:
{
  "domain": "example.com",
  "company_name": "Example Inc" (optional)
}

Returns:
{
  "success": true,
  "domain": "example.com",
  "pricing_page_url": "https://example.com/pricing",
  "confidence": "high" | "medium" | "low",
  "explanation": "Found /pricing link in main navigation"
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
def discover_pricing_page_url(request: dict) -> dict:
    import requests
    from bs4 import BeautifulSoup
    import google.generativeai as genai
    from supabase import create_client
    import re

    # Setup clients
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        company_name = request.get("company_name", "")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # Normalize domain (remove protocol if present)
        domain = re.sub(r'^https?://', '', domain)
        domain = domain.rstrip('/')

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("discover_pricing_page_payloads")
            .insert({
                "domain": domain,
                "company_name": company_name,
                "payload": request,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Fetch the company homepage
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        homepage_url = f"https://{domain}"
        try:
            response = requests.get(homepage_url, headers=headers, timeout=15, allow_redirects=True)
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to fetch homepage: HTTP {response.status_code}",
                    "domain": domain,
                    "raw_payload_id": str(raw_payload_id),
                }
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Homepage fetch timeout", "domain": domain}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Homepage connection error", "domain": domain}

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract all links with their text
        links = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if href and text:
                # Normalize href
                if href.startswith("/"):
                    href = f"https://{domain}{href}"
                elif not href.startswith("http"):
                    href = f"https://{domain}/{href}"
                links.append({"href": href, "text": text})

        # Also get page text for context
        for script in soup(["script", "style"]):
            script.decompose()
        page_text = soup.get_text(separator=" ", strip=True)[:4000]

        # Format links for Gemini
        links_text = "\n".join([f"- {l['text']}: {l['href']}" for l in links[:100]])

        # 3. Send to Gemini to find pricing page
        company_context = f"Company: {company_name}" if company_name else f"Domain: {domain}"

        prompt = f"""Analyze this website and find the pricing page URL.

{company_context}
Homepage: {homepage_url}

Links found on the page:
{links_text}

Page content excerpt:
{page_text}

Your task: Find the URL that leads to the company's pricing page.

Look for:
- Links with text like "Pricing", "Plans", "Plans & Pricing", "Get Started", "See Plans"
- Common URL patterns like /pricing, /plans, /packages, /pricing-plans

If you find a clear pricing page link, report it with HIGH confidence.
If you find a likely candidate but aren't certain, report it with MEDIUM confidence.
If you cannot find any pricing page link, report null with LOW confidence.

Respond in this exact JSON format:
{{"pricing_page_url": "https://example.com/pricing or null", "confidence": "high|medium|low", "explanation": "1-2 sentence explanation"}}

Only return the JSON, nothing else."""

        model = genai.GenerativeModel("gemini-2.0-flash")
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
            pricing_page_url = result.get("pricing_page_url")
            confidence = result.get("confidence", "low").lower()
            explanation = result.get("explanation", "")
        except json.JSONDecodeError:
            pricing_page_url = None
            confidence = "low"
            explanation = f"Failed to parse Gemini response: {response_text[:200]}"

        # Handle "null" string
        if pricing_page_url == "null" or pricing_page_url == "None":
            pricing_page_url = None

        # Validate confidence
        if confidence not in ["high", "medium", "low"]:
            confidence = "low"

        # 4. Insert into extracted
        supabase.schema("extracted").from_("discover_pricing_page").insert({
            "raw_payload_id": raw_payload_id,
            "domain": domain,
            "pricing_page_url": pricing_page_url,
            "confidence": confidence,
            "explanation": explanation,
        }).execute()

        # 5. If we found a pricing page URL with high/medium confidence, upsert into core.ancillary_urls
        if pricing_page_url and confidence in ["high", "medium"]:
            supabase.schema("core").from_("ancillary_urls").upsert({
                "domain": domain,
                "pricing_page_url": pricing_page_url,
                "updated_at": "now()",
            }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "pricing_page_url": pricing_page_url,
            "confidence": confidence,
            "explanation": explanation,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
