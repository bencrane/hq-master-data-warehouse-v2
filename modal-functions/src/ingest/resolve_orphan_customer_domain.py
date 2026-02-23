"""
Resolve Orphan Customer Domain using Gemini

For customers where we only have the name - no case study URL, no existing domain match.
Uses origin company context (industry, description) to disambiguate which company we're looking for.

Expects:
{
  "customer_company_name": "Mercury",
  "origin_company_name": "Ramp",
  "origin_company_domain": "ramp.com",
  "origin_company_industry": "Fintech",
  "origin_company_description": "Corporate cards and spend management platform"
}

Returns:
{
  "success": true,
  "customer_company_name": "Mercury",
  "domain": "mercury.com",
  "confidence": "high",
  "reason": "Mercury is a fintech startup offering banking for startups, aligns with B2B fintech context",
  "input_tokens": 150,
  "output_tokens": 50,
  "cost_usd": 0.00004
}
"""

import os
import json
import modal
from config import app, image


PROMPT_TEMPLATE = """You are a B2B company identification expert. Find the website domain for a company given its name and business context.

**Company to find:** "{customer_company_name}"

**Context - this company is a customer of:**
- Vendor: {origin_company_name} ({origin_company_domain})
- Vendor industry: {origin_company_industry}
- Vendor description: {origin_company_description}

**Use this context to disambiguate:**
- Think about what {origin_company_name} sells and what kinds of companies would buy their product/service
- If the customer name is ambiguous (e.g., "Mercury" could be many companies), use the B2B context to pick the most likely match
- A fintech vendor's customer named "Mercury" is probably mercury.com (the banking startup), not a car brand
- Consider common abbreviations: "AWS" = amazon.com, "JPM" = jpmorgan.com, "MSFT" = microsoft.com

**Rules:**
- Return ONLY the bare domain (e.g., "stripe.com", not "https://www.stripe.com")
- If the company is a subsidiary or division, return the parent company's primary domain
- "high" confidence = you found clear evidence this is the company's official domain
- "medium" confidence = likely correct but some ambiguity exists
- "low" confidence = best guess based on name pattern
- If you truly cannot determine the domain, return null for domain

**Return ONLY valid JSON:**
{{
  "domain": "example.com",
  "confidence": "high",
  "reason": "Brief explanation"
}}
"""


@app.function(
    image=image,
    timeout=60,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def resolve_orphan_customer_domain(request: dict) -> dict:
    from supabase import create_client
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        customer_company_name = request.get("customer_company_name", "").strip()
        origin_company_name = request.get("origin_company_name", "").strip()
        origin_company_domain = request.get("origin_company_domain", "").strip()
        origin_company_industry = request.get("origin_company_industry", "").strip() or "Unknown"
        origin_company_description = request.get("origin_company_description", "").strip() or "No description available"

        if not customer_company_name:
            return {"success": False, "error": "customer_company_name is required"}
        if not origin_company_domain:
            return {"success": False, "error": "origin_company_domain is required"}

        prompt = PROMPT_TEMPLATE.format(
            customer_company_name=customer_company_name,
            origin_company_name=origin_company_name or origin_company_domain,
            origin_company_domain=origin_company_domain,
            origin_company_industry=origin_company_industry,
            origin_company_description=origin_company_description,
        )

        model = genai.GenerativeModel("gemini-2.0-flash")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        response_text = response.text.strip()

        # Get token counts
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        # Gemini 2.0 Flash pricing: $0.10/1M input, $0.40/1M output
        cost_usd = (input_tokens * 0.10 / 1_000_000) + (output_tokens * 0.40 / 1_000_000)

        try:
            result = json.loads(response_text)
            domain = result.get("domain")
            confidence = result.get("confidence", "low")
            reason = result.get("reason", "")
        except json.JSONDecodeError:
            domain = None
            confidence = "none"
            reason = "Failed to parse response"

        # Store raw payload
        try:
            supabase.schema("raw").from_("resolve_customer_domain_payloads").insert({
                "customer_name": customer_company_name,
                "origin_company_name": origin_company_name,
                "origin_company_domain": origin_company_domain,
                "customer_domain": domain,
                "confidence": confidence,
                "reasoning": reason,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost_usd,
            }).execute()
        except Exception:
            pass

        # Update core.company_customers if domain resolved
        if domain:
            try:
                supabase.schema("core").from_("company_customers").update({
                    "customer_domain": domain,
                    "customer_domain_source": "gemini-orphan-resolve",
                }).eq(
                    "origin_company_domain", origin_company_domain
                ).eq(
                    "customer_name", customer_company_name
                ).is_(
                    "customer_domain", "null"
                ).execute()
            except Exception:
                pass

        return {
            "success": True,
            "customer_company_name": customer_company_name,
            "origin_company_domain": origin_company_domain,
            "domain": domain,
            "confidence": confidence,
            "reason": reason,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "customer_company_name": request.get("customer_company_name", "unknown"),
        }
