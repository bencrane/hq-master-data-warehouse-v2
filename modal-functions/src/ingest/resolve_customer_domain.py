"""
Resolve Customer Domain Endpoint

Given a customer company name and the origin company context,
uses Gemini 3 Flash to resolve the customer's website domain.
Updates core.company_customers with the result.
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional
from config import app, image


class ResolveCustomerDomainRequest(BaseModel):
    id: str
    customer_name: str
    origin_company_name: str
    origin_company_domain: str


RESOLVE_PROMPT = """You are a B2B company identification expert. Your job is to determine the website domain of a company based on its name and business context.

**Known fact:** "{customer_name}" is a verified customer of {origin_company_name} ({origin_company_domain}).

**Use this context intelligently:**
- {origin_company_name} is a B2B company at {origin_company_domain}. Think about what {origin_company_name} sells and what kinds of companies would buy their product/service.
- The customer "{customer_name}" uses {origin_company_name}'s product. This tells you the customer is likely in an industry or of a size that would need what {origin_company_name} offers.
- If the customer name is ambiguous (e.g., "Mercury" could be many companies), use the B2B context to pick the most likely match. A fintech company's customer named "Mercury" is probably mercury.com (the banking startup), not a car brand.
- Consider common name variations: "AWS" = amazon.com, "Google Cloud" = google.com, "JPM" = jpmorgan.com

**Rules:**
- Return ONLY the bare domain (e.g., "stripe.com", not "https://www.stripe.com")
- If the company is a well-known brand, subsidiary, or division, return the parent company's primary domain
- If you cannot confidently determine the domain, return null — do not guess
- Confidence should be "high" only if you are very sure of the match

**Response Format:**
Return ONLY valid JSON:
{{
    "customer_domain": "example.com" or null,
    "confidence": "high", "medium", or "low",
    "reasoning": "1-2 sentences explaining your determination"
}}
"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=120,
)
@modal.fastapi_endpoint(method="POST")
def resolve_customer_domain(request: ResolveCustomerDomainRequest) -> dict:
    from supabase import create_client
    import google.generativeai as genai

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        prompt = RESOLVE_PROMPT.format(
            customer_name=request.customer_name,
            origin_company_name=request.origin_company_name,
            origin_company_domain=request.origin_company_domain,
        )

        model = genai.GenerativeModel("gemini-3-flash-preview")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        try:
            gemini_response = json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse Gemini response as JSON",
                "raw_response": response.text,
            }

        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        total_tokens = input_tokens + output_tokens
        cost_usd = (input_tokens * 0.50 / 1_000_000) + (output_tokens * 3.00 / 1_000_000)

        customer_domain = gemini_response.get("customer_domain")
        confidence = gemini_response.get("confidence")

        if customer_domain:
            try:
                supabase.schema("core").from_("company_customers").update({
                    "customer_domain": customer_domain,
                    "customer_domain_source": "gemini-3-flash-preview",
                }).eq("id", request.id).execute()
            except Exception:
                pass

        return {
            "success": True,
            "id": request.id,
            "customer_name": request.customer_name,
            "origin_company_name": request.origin_company_name,
            "origin_company_domain": request.origin_company_domain,
            "customer_domain": customer_domain,
            "confidence": confidence,
            "reasoning": gemini_response.get("reasoning"),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
