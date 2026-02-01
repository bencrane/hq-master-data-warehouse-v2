"""
Webinars Extraction

Uses Gemini to analyze a company's homepage and extract webinar data.

Expects:
{
  "company_name": "Example Inc",
  "domain": "example.com"
}

Returns:
{
  "has_webinars": true/false,
  "webinar_count": 3,
  "webinars": [
    {"url": "/webinars/ai-automation", "title": "AI Automation Best Practices", "topic": "AI"},
    ...
  ],
  "webinar_topics": ["AI", "Sales", "Marketing"]
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
def infer_webinars(request: dict) -> dict:
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
            .from_("webinars_payloads")
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

        links_text = "\n".join(links[:300])

        # 3. Send to Gemini for extraction
        company_context = f"Company: {company_name}" if company_name else f"Domain: {domain}"

        prompt = f"""Analyze this company's homepage and extract all webinar-related pages.

{company_context}
Homepage URL: {homepage_url}

Links found on homepage:
{links_text}

Look for webinar pages like:
- "Webinars", "Webinar", "Live Events", "Virtual Events"
- "On-demand webinars", "Upcoming webinars"
- URLs containing /webinar, /webinars, /events, /live
- Specific webinar titles with registration links

For each webinar or webinar page found, extract:
1. The URL (relative or absolute)
2. The title/link text
3. The topic/category if identifiable (e.g., "Sales", "Product Demo", "Industry Trends")

Respond in this exact JSON format:
{{
  "webinars": [
    {{"url": "/webinars/sales-automation", "title": "Sales Automation Masterclass", "topic": "Sales"}},
    {{"url": "/events/product-demo", "title": "Live Product Demo", "topic": "Product"}}
  ]
}}

If no webinar pages found, return: {{"webinars": []}}

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
            webinars = result.get("webinars", [])
        except json.JSONDecodeError:
            webinars = []

        # 4. Insert each webinar into extracted
        webinar_topics = []
        for webinar in webinars:
            if not isinstance(webinar, dict):
                continue

            topic = webinar.get("topic", "")
            if topic and topic not in webinar_topics:
                webinar_topics.append(topic)

            supabase.schema("extracted").from_("company_webinars").insert({
                "raw_payload_id": raw_payload_id,
                "domain": domain,
                "webinar_url": webinar.get("url", ""),
                "webinar_title": webinar.get("title", ""),
                "webinar_topic": topic,
            }).execute()

        # 5. Upsert into core
        has_webinars = len(webinars) > 0
        webinar_count = len(webinars)

        supabase.schema("core").from_("company_webinars").upsert({
            "domain": domain,
            "has_webinars": has_webinars,
            "webinar_count": webinar_count,
            "webinar_topics": webinar_topics,
            "last_checked_at": "now()",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "has_webinars": has_webinars,
            "webinar_count": webinar_count,
            "webinars": webinars,
            "webinar_topics": webinar_topics,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
