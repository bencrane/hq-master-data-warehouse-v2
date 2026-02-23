"""
Infer Customer Domain using Gemini with Google Search

Uses Gemini 2.0 Flash with grounding to search for and infer the customer company's domain
based on context from the origin company and case study.

Expects:
{
  "customer_company_name": "Carrefour Italy",
  "origin_company_name": "Appier",
  "origin_company_domain": "appier.com",
  "origin_company_description": "Appier is an AI-powered marketing platform..." (optional),
  "origin_company_industry": "Marketing Technology" (optional),
  "case_study_url": "https://appier.com/success-stories/carrefour" (optional)
}

Returns:
{
  "success": true,
  "customer_company_name": "Carrefour Italy",
  "candidates": [
    {"domain": "carrefour.it", "confidence": "high", "reason": "Italian subsidiary of Carrefour"},
  ],
  "input_tokens": 150,
  "output_tokens": 50,
  "cost_usd": 0.00004
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
def infer_customer_domain(request: dict) -> dict:
    import google.generativeai as genai
    import json

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    try:
        customer_company_name = request.get("customer_company_name", "").strip()
        origin_company_name = request.get("origin_company_name", "").strip()
        origin_company_domain = request.get("origin_company_domain", "").strip()
        origin_company_description = request.get("origin_company_description", "").strip()
        origin_company_industry = request.get("origin_company_industry", "").strip()
        case_study_url = request.get("case_study_url", "").strip()

        if not customer_company_name:
            return {"success": False, "error": "customer_company_name is required"}

        # Build context
        context_parts = []
        if origin_company_name:
            context_parts.append(f"Origin company: {origin_company_name}")
        if origin_company_domain:
            context_parts.append(f"Origin company domain: {origin_company_domain}")
        if origin_company_industry:
            context_parts.append(f"Origin company industry: {origin_company_industry}")
        if origin_company_description:
            context_parts.append(f"Origin company description: {origin_company_description}")
        if case_study_url:
            context_parts.append(f"Case study URL: {case_study_url}")

        context = "\n".join(context_parts) if context_parts else "No additional context"

        prompt = f"""Find the website domain for this company.

Company to find: "{customer_company_name}"

Context (this company is a customer of):
{context}

Search for the company's official website domain. Use the context to help disambiguate -
for example if the origin company is a B2B SaaS company, the customer is likely a business, not a consumer brand with the same name.

Return JSON only with 1-3 most likely domain candidates:
{{
  "candidates": [
    {{"domain": "example.com", "confidence": "high/medium/low", "reason": "Brief explanation"}}
  ]
}}

Rules:
- Return actual domains (e.g., "carrefour.it") not URLs
- If you can't find a likely domain, return empty candidates array
- "high" confidence = you found clear evidence this is the company's domain
- "medium" confidence = likely but not 100% certain
- "low" confidence = best guess based on name pattern

Return only valid JSON, nothing else."""

        model = genai.GenerativeModel("gemini-3.0-flash")

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Get token counts
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 3.0 Flash pricing
        cost_usd = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)

        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        try:
            result = json.loads(response_text)
            candidates = result.get("candidates", [])
        except json.JSONDecodeError:
            candidates = []

        return {
            "success": True,
            "customer_company_name": customer_company_name,
            "candidates": candidates,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 6)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "customer_company_name": request.get("customer_company_name", "unknown"),
        }
