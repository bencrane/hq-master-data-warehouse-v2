"""
Discover Competitors using OpenAI

Uses OpenAI to find top 3-5 competitors of a company.

Expects:
{
  "company_name": "Stripe",
  "domain": "stripe.com"
}

Returns:
{
  "success": true,
  "competitors": [
    {"name": "Adyen", "domain": "adyen.com", "linkedin_url": "https://linkedin.com/company/adyen"},
    ...
  ]
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
        modal.Secret.from_name("openai-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def discover_competitors_openai(request: dict) -> dict:
    import openai
    import json

    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    try:
        company_name = request.get("company_name", "").strip()
        domain = request.get("domain", "").lower().strip()

        if not company_name:
            return {"success": False, "error": "No company_name provided"}

        prompt = f"""Who are the top 3-5 direct competitors of {company_name}?
Domain: {domain}

Return a JSON array of competitors. For each competitor, provide:
- name: company name
- domain: company website domain (e.g., "adyen.com")
- linkedin_url: LinkedIn company page URL (e.g., "https://linkedin.com/company/adyen")

Return ONLY valid JSON in this exact format, nothing else:
[
  {{"name": "Competitor Name", "domain": "competitor.com", "linkedin_url": "https://linkedin.com/company/competitor"}}
]"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        response_text = response.choices[0].message.content.strip()

        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        response_text = response_text.strip()

        try:
            competitors = json.loads(response_text)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse OpenAI response",
                "raw_response": response_text[:500]
            }

        return {
            "success": True,
            "company_name": company_name,
            "domain": domain,
            "competitors": competitors
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "company_name": request.get("company_name", "unknown"),
        }
