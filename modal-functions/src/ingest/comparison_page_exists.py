"""
Comparison Pages Extraction

Uses Gemini to analyze a company's homepage and extract comparison page data.

Expects:
{
  "company_name": "Example Inc",
  "domain": "example.com"
}

Returns:
{
  "has_comparison_pages": true/false,
  "comparison_count": 3,
  "comparison_pages": [
    {"url": "/vs-salesforce", "title": "Acme vs Salesforce", "competitor": "Salesforce"},
    ...
  ],
  "competitors_mentioned": ["Salesforce", "HubSpot", "Zendesk"]
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
def infer_comparison_page_exists(request: dict) -> dict:
    import requests
    from bs4 import BeautifulSoup
    import google.generativeai as genai
    from supabase import create_client

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        domain = request.get("domain", "").lower().strip()
        company_name = request.get("company_name", "")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("comparison_page_exists_payloads")
            .insert({
                "domain": domain,
                "company_name": company_name,
                "payload": request,
            })
            .execute()
        )
        raw_payload_id = raw_insert.data[0]["id"]

        # 2. Fetch homepage content
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

        # Parse HTML - keep links for analysis
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract all links with their text and href
        links = []
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if href and text:
                links.append(f"{text} -> {href}")

        links_text = "\n".join(links[:300])  # Limit to 300 links

        # 3. Send to Gemini for extraction
        company_context = f"Company: {company_name}" if company_name else f"Domain: {domain}"

        prompt = f"""Analyze this company's homepage and extract all comparison pages.

{company_context}
Homepage URL: {homepage_url}

Links found on homepage:
{links_text}

Look for comparison pages like:
- "X vs Y" pages
- "Alternative to X" pages
- "Compare" pages
- "Why choose us over X" pages
- URLs containing /vs/, /compare, /alternatives, /versus

For each comparison page found, extract:
1. The URL (relative or absolute)
2. The title/link text
3. The competitor being compared (if identifiable)

Respond in this exact JSON format:
{{
  "comparison_pages": [
    {{"url": "/vs-salesforce", "title": "Acme vs Salesforce", "competitor": "Salesforce"}},
    {{"url": "/alternatives/hubspot", "title": "HubSpot Alternative", "competitor": "HubSpot"}}
  ]
}}

If no comparison pages found, return: {{"comparison_pages": []}}

Only return the JSON, nothing else."""

        model = genai.GenerativeModel("gemini-3-flash-preview")
        gemini_response = model.generate_content(prompt)

        # Parse Gemini response
        import json
        response_text = gemini_response.text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        try:
            result = json.loads(response_text)
            comparison_pages = result.get("comparison_pages", [])
        except json.JSONDecodeError:
            comparison_pages = []

        # 4. Insert each comparison page into extracted
        competitors_mentioned = []
        for page in comparison_pages:
            if not isinstance(page, dict):
                continue

            competitor = page.get("competitor", "")
            if competitor and competitor not in competitors_mentioned:
                competitors_mentioned.append(competitor)

            supabase.schema("extracted").from_("company_comparison_pages").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "comparison_url": page.get("url", ""),
                "comparison_title": page.get("title", ""),
                "competitor_mentioned": competitor,
            }).execute()

        # 5. Upsert into core
        has_comparison_pages = len(comparison_pages) > 0
        comparison_count = len(comparison_pages)

        supabase.schema("core").from_("company_comparison_pages").upsert({
            "domain": domain,
            "has_comparison_pages": has_comparison_pages,
            "comparison_count": comparison_count,
            "competitors_mentioned": competitors_mentioned,
            "last_checked_at": "now()",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "has_comparison_pages": has_comparison_pages,
            "comparison_count": comparison_count,
            "comparison_pages": comparison_pages,
            "competitors_mentioned": competitors_mentioned,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
