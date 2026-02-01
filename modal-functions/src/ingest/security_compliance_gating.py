"""
Security Compliance Gating Inference

Uses Gemini to analyze a company's pricing page and determine if security/compliance features are gated to higher tiers.

Expects:
{
  "company_name": "Example Inc",
  "domain": "example.com",
  "pricing_page_url": "https://example.com/pricing"
}

Returns:
{
  "security_compliance_gating": "yes" | "no" | "not_mentioned",
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
def infer_security_gating(request: dict) -> dict:
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
        pricing_page_url = request.get("pricing_page_url", "").strip()
        company_name = request.get("company_name", "")

        if not domain:
            return {"success": False, "error": "No domain provided"}

        if not pricing_page_url:
            return {"success": False, "error": "No pricing_page_url provided"}

        # 1. Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("security_compliance_gating_payloads")
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
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        page_text = soup.get_text(separator=" ", strip=True)[:8000]

        # 3. Send to Gemini for classification
        company_context = f"Company: {company_name}" if company_name else f"Domain: {domain}"

        prompt = f"""Analyze this pricing page content and determine if security/compliance features are gated to higher tiers.

{company_context}
Pricing Page URL: {pricing_page_url}

Pricing Page Content:
{page_text}

Security/compliance features include: SSO, SAML, SOC2, HIPAA, GDPR compliance, audit logs, role-based access control (RBAC), custom security reviews, dedicated support, SLAs, etc.

Classify as ONE of:
- yes: Security/compliance features are clearly gated to higher tiers (e.g., SSO only on Enterprise)
- no: Security/compliance features are available on all tiers or included in base plan
- not_mentioned: Pricing page doesn't discuss security/compliance features

Respond in this exact JSON format:
{{"security_compliance_gating": "yes|no|not_mentioned", "explanation": "1-2 sentence explanation"}}

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
            security_compliance_gating = result.get("security_compliance_gating", "").lower()
            explanation = result.get("explanation", "")
        except json.JSONDecodeError:
            security_compliance_gating = "unknown"
            explanation = response_text

        valid_values = ["yes", "no", "not_mentioned"]
        if security_compliance_gating not in valid_values:
            security_compliance_gating = "unknown"

        # 4. Insert into extracted
        supabase.schema("extracted").from_("company_security_compliance_gating").insert({
            "raw_payload_id": raw_payload_id,
            "domain": domain,
            "pricing_page_url": pricing_page_url,
            "security_compliance_gating": security_compliance_gating,
            "explanation": explanation,
        }).execute()

        # 5. Upsert into core
        supabase.schema("core").from_("company_security_compliance_gating").upsert({
            "domain": domain,
            "security_compliance_gating": security_compliance_gating,
            "explanation": explanation,
            "last_checked_at": "now()",
        }, on_conflict="domain").execute()

        return {
            "success": True,
            "domain": domain,
            "raw_payload_id": str(raw_payload_id),
            "security_compliance_gating": security_compliance_gating,
            "explanation": explanation,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.get("domain", "unknown"),
        }
