"""
Get Customers Of - Gemini Web Scraper

Uses Gemini 3 Flash Preview to find all customers of a company by searching
their website AND across the web for evidence of customer relationships.

Expects:
{
  "domain": "example.com",
  "company_name": "Example Inc" (optional)
}

Returns:
{
  "success": true,
  "domain": "example.com",
  "customers": [
    {
      "company_name": "Customer A",
      "domain": "customera.com",
      "evidence_url": "https://example.com/case-studies/customer-a"
    }
  ],
  "customer_count": 2,
  "input_tokens": 1500,
  "output_tokens": 200,
  "cost_usd": 0.00135
}
"""

import os
import json
import modal
from pydantic import BaseModel
from typing import Optional, List

from config import app, image


class GetCustomersOfRequest(BaseModel):
    domain: str
    company_name: Optional[str] = None


PROMPT_TEMPLATE = """#CONTEXT#

You are an AI-powered research agent specialized in identifying B2B customer relationships. You have the ability to browse the web and find evidence of companies using other companies' products or services.

#OBJECTIVE#

Find all customers of {company_name} ({url}). Search both their website AND across the web for evidence of customer relationships.

#INSTRUCTIONS#

1) Search the company's website at {url}:
   - Look for: Customers, Case Studies, Testimonials, Success Stories, References, Our Clients, Who We Work With, logo walls
   - Extract customer company names from these pages

2) Search beyond the website:
   - Find mentions of {company_name}'s customers in press releases, news articles, review sites (G2, Capterra), blog posts, LinkedIn, Twitter/X, etc.
   - Look for phrases like "uses {company_name}", "powered by {company_name}", "switched to {company_name}", "{company_name} customer"

3) For each customer found:
   - company_name: The customer company's name
   - domain: The customer company's website domain (e.g., "acme.com"). If unknown, return empty string.
   - evidence_url: The URL where you found evidence of this customer relationship (case study, press release, review, news article, etc.)

4) Rules:
   - Only include companies where you have clear evidence they are customers
   - Do not guess or infer - only return customers you can attribute to a specific URL
   - Normalize company names (trim whitespace, remove trademark symbols)
   - Deduplicate by company name - if found in multiple places, prefer case study URLs as evidence

5) Output format:
   Return a JSON array:
   [
     {{"company_name": "Acme Corp", "domain": "acme.com", "evidence_url": "https://example.com/case-studies/acme"}},
     {{"company_name": "Beta Inc", "domain": "beta.io", "evidence_url": "https://www.g2.com/products/example/reviews"}}
   ]

#EXAMPLE#

Finding customers of Vanta (vanta.com):

[
  {{"company_name": "Notion", "domain": "notion.so", "evidence_url": "https://vanta.com/customers/notion"}},
  {{"company_name": "Lattice", "domain": "lattice.com", "evidence_url": "https://vanta.com/case-studies/lattice"}},
  {{"company_name": "Calm", "domain": "calm.com", "evidence_url": "https://techcrunch.com/2023/04/calm-security-vanta"}}
]

Now find all customers of {company_name} ({url}):"""


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
    timeout=300,  # 5 minutes - web scraping across multiple sites
)
@modal.fastapi_endpoint(method="POST")
def get_customers_of(request: GetCustomersOfRequest) -> dict:
    """
    Scrape a company's website using Gemini to find their customers.
    Stores raw payload and upserts customers to core.company_customers.
    """
    from supabase import create_client
    import google.generativeai as genai

    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    gemini_api_key = os.environ["GEMINI_API_KEY"]
    genai.configure(api_key=gemini_api_key)

    try:
        # Normalize domain
        domain = request.domain.lower().strip()
        if domain.startswith("http://") or domain.startswith("https://"):
            domain = domain.split("://")[1]
        if domain.startswith("www."):
            domain = domain[4:]
        domain = domain.rstrip("/")

        url = f"https://{domain}"
        company_name = request.company_name or domain

        # Build prompt
        prompt = PROMPT_TEMPLATE.format(url=url, company_name=company_name)

        # Call Gemini 3 Flash Preview
        model = genai.GenerativeModel("gemini-3-flash-preview")

        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,  # Low temperature for consistent extraction
            ),
        )

        # Extract token usage
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        # Gemini 3 Flash Preview pricing: $0.50/1M input, $3.00/1M output
        cost_usd = (input_tokens * 0.50 / 1_000_000) + (output_tokens * 3.00 / 1_000_000)

        # Parse Gemini response
        try:
            customers_raw = json.loads(response.text)
            if not isinstance(customers_raw, list):
                customers_raw = []
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse Gemini response as JSON",
                "raw_response": response.text[:2000],
                "domain": domain,
            }

        # Normalize and validate customers
        customers = []
        for c in customers_raw:
            if isinstance(c, dict) and c.get("company_name"):
                customers.append({
                    "company_name": c.get("company_name", "").strip(),
                    "domain": (c.get("domain", "") or "").lower().strip(),
                    "evidence_url": c.get("evidence_url", "") or "",
                })

        # Store raw payload
        raw_insert = (
            supabase.schema("raw")
            .from_("gemini_customers_of_payloads")
            .insert({
                "origin_company_domain": domain,
                "origin_company_name": company_name,
                "raw_payload": {
                    "customers": customers,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost_usd": cost_usd,
                },
            })
            .execute()
        )
        raw_id = raw_insert.data[0]["id"] if raw_insert.data else None

        # Upsert to core.company_customers
        upserted_count = 0
        for c in customers:
            try:
                supabase.schema("core").from_("company_customers").upsert(
                    {
                        "origin_company_domain": domain,
                        "origin_company_name": company_name,
                        "customer_name": c["company_name"],
                        "customer_domain": c["domain"] if c["domain"] else None,
                        "case_study_url": c["evidence_url"] if c["evidence_url"] else None,
                        "has_case_study": bool(c["evidence_url"]),
                        "source": "gemini-get-customers-of",
                        "source_id": raw_id,
                    },
                    on_conflict="origin_company_domain,customer_name",
                ).execute()
                upserted_count += 1
            except Exception:
                pass  # Non-fatal — continue with other customers

        return {
            "success": True,
            "domain": domain,
            "company_name": company_name,
            "raw_id": str(raw_id) if raw_id else None,
            "customers": customers,
            "customer_count": len(customers),
            "upserted_count": upserted_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "domain": request.domain,
        }
