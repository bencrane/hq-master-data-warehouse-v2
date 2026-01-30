"""
Industry Inference

Uses Gemini to infer industry from company name, domain, and description.
Then fuzzy matches against reference.industry_lookup.
"""

import os
import modal
from pydantic import BaseModel
from typing import Optional, List

from config import app, image


class IndustryInferenceRequest(BaseModel):
    company_name: str
    domain: Optional[str] = None
    short_description: Optional[str] = None


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("supabase-credentials"),
        modal.Secret.from_name("gemini-secret"),
    ],
)
@modal.fastapi_endpoint(method="POST")
def infer_company_industry(request: IndustryInferenceRequest) -> dict:
    """
    Infer company industry using Gemini, then match against reference industries.
    """
    import google.generativeai as genai
    from supabase import create_client

    # Setup clients
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_SERVICE_KEY"]
    supabase = create_client(supabase_url, supabase_key)

    try:
        # Build prompt for Gemini
        prompt = f"""Given the following company information, return the most likely industry or industries (up to 3).

Company Name: {request.company_name}
Description: {request.short_description or 'N/A'}

Return only the industry names, one per line. Be specific but use common industry terminology.
"""

        # Call Gemini
        model = genai.GenerativeModel("gemini-3-flash-preview")
        response = model.generate_content(prompt)

        # Extract token usage and calculate cost
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        # Gemini 2.0 Flash pricing: $0.10/1M input, $0.40/1M output
        cost_usd = (input_tokens * 0.10 / 1_000_000) + (output_tokens * 0.40 / 1_000_000)

        gemini_industries = []
        for line in response.text.strip().split("\n"):
            cleaned = line.strip()
            # Strip bullet points and markdown formatting
            cleaned = cleaned.lstrip("*-•").strip()
            if cleaned:
                gemini_industries.append(cleaned)

        # Fuzzy match each against reference.industry_lookup
        matched_industries = []
        for gemini_industry in gemini_industries[:3]:  # Max 3
            # Try exact match first
            exact_result = (
                supabase.schema("reference")
                .from_("industry_lookup")
                .select("industry_cleaned")
                .ilike("industry_cleaned", gemini_industry)
                .limit(1)
                .execute()
            )

            if exact_result.data:
                matched_industries.append({
                    "gemini_guess": gemini_industry,
                    "matched_industry": exact_result.data[0]["industry_cleaned"],
                    "match_type": "exact",
                })
                continue

            # Try fuzzy match with ILIKE %word%
            words = gemini_industry.split()
            for word in words:
                if len(word) < 4:
                    continue
                fuzzy_result = (
                    supabase.schema("reference")
                    .from_("industry_lookup")
                    .select("industry_cleaned")
                    .ilike("industry_cleaned", f"%{word}%")
                    .limit(3)
                    .execute()
                )
                if fuzzy_result.data:
                    matched_industries.append({
                        "gemini_guess": gemini_industry,
                        "matched_industry": fuzzy_result.data[0]["industry_cleaned"],
                        "match_type": "fuzzy",
                        "match_word": word,
                        "alternatives": [r["industry_cleaned"] for r in fuzzy_result.data[1:]],
                    })
                    break
            else:
                # No match found
                matched_industries.append({
                    "gemini_guess": gemini_industry,
                    "matched_industry": None,
                    "match_type": "no_match",
                })

        return {
            "success": True,
            "company_name": request.company_name,
            "gemini_raw": gemini_industries,
            "matched_industries": matched_industries,
            "best_match": next((m["matched_industry"] for m in matched_industries if m["matched_industry"]), None),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
