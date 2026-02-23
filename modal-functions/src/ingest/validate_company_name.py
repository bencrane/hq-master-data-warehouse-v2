"""
Validate Company Name

Uses GPT-4 to determine if a company name is a real company or a generic placeholder,
and returns a normalized version if real.

Expects:
{
  "company_name": "Carrefour Italy"
}

Returns:
{
  "success": true,
  "company_name": "Carrefour Italy",
  "is_real_company": true,
  "normalized_name": "Carrefour Italy",
  "confidence": "high",
  "reason": "Carrefour is a well-known retail chain"
}

Or for generic names:
{
  "success": true,
  "company_name": "A Fortune 500 Company",
  "is_real_company": false,
  "normalized_name": null,
  "confidence": "high",
  "reason": "Generic placeholder, not a specific company"
}
"""

import os
import modal
from config import app, image


@app.function(
    image=image,
    timeout=30,
    secrets=[
        modal.Secret.from_name("openai-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def validate_company_name(request: dict) -> dict:
    import openai
    import json

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    try:
        company_name = request.get("company_name", "").strip()

        if not company_name:
            return {"success": False, "error": "company_name is required"}

        prompt = f"""Analyze this company name and determine if it refers to a real, specific company or is a generic placeholder.

Company name: "{company_name}"

Generic/placeholder examples (NOT real companies):
- "A Fortune 500 Company"
- "Regional Carrier"
- "B2B Professional Services Company"
- "Leading Healthcare Provider"
- "Top Beverage Brand"
- "Global Consulting Firm"
- "Major Retailer"

Real company examples:
- "Carrefour Italy" (real: Carrefour is a specific retailer)
- "Baxter Healthcare" (real: Baxter is a specific company)
- "Mobile Technologies Inc." (real: has Inc. suffix = legally incorporated)

CRITICAL RULE: If a company name has a legal suffix like Inc., LLC, Ltd, Corp, Corporation, GmbH, S.A., Co., etc.,
it IS a real company - they legally incorporated. ALWAYS mark these as is_real_company: true, regardless of how generic the name sounds.
"Mobile Technologies Inc." = REAL (has Inc.)
"Generic Solutions LLC" = REAL (has LLC)
"Regional Carrier" = NOT REAL (no legal suffix, clearly a placeholder)

Return JSON only:
{{
  "is_real_company": true/false,
  "normalized_name": "Cleaned company name" or null if not real,
  "confidence": "high"/"medium"/"low",
  "reason": "Brief explanation"
}}

If real, normalize the name:
- Remove trailing punctuation
- Fix obvious typos
- Keep suffixes like Inc, LLC, Ltd if present
- Keep location qualifiers like "Carrefour Italy"

Return only valid JSON, nothing else."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )

        response_text = response.choices[0].message.content.strip()

        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse GPT response",
                "raw_response": response_text[:500]
            }

        return {
            "success": True,
            "company_name": company_name,
            "is_real_company": result.get("is_real_company", False),
            "normalized_name": result.get("normalized_name"),
            "confidence": result.get("confidence", "low"),
            "reason": result.get("reason", "")
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "company_name": request.get("company_name", "unknown"),
        }
